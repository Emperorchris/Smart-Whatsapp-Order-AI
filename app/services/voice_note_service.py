"""Voice note transcription service.

Flow:
  1. Receives a WhatsApp audio media_id
  2. Downloads the audio bytes via whatsapp_service.download_media()
  3. Uploads the audio to Cloudinary (so admins can listen from the dashboard)
  4. Writes to a temp file (Whisper API requires a file, not raw bytes)
  5. Sends to OpenAI Whisper for transcription
  6. Returns both the transcribed text AND the Cloudinary URL

Whisper handles: English, Pidgin, Yoruba, Hausa, Igbo, and code-switching
(mixing languages in one sentence — very common in Nigerian conversations).
"""

import tempfile
import os
from dataclasses import dataclass

import cloudinary.uploader
from openai import AsyncOpenAI
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Config
from ..core import utils, exceptions
from ..db.schemas.message_schema import MessageSchema
from . import whatsapp_service, message_service



_openai_client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)

# Max voice note size we'll process (16MB — WhatsApp's limit)
MAX_AUDIO_SIZE = 16 * 1024 * 1024


@dataclass
class VoiceNoteResult:
    """Result of voice note processing."""
    text: str | None           # The transcribed text (None if transcription failed)
    audio_url: str | None      # Cloudinary URL for dashboard playback


async def transcribe_voice_note(media_id: str) -> VoiceNoteResult:
    """Download a WhatsApp voice note, save to Cloudinary, and transcribe it.

    Args:
        media_id: The WhatsApp media ID from the webhook payload.

    Returns:
        VoiceNoteResult with text and audio_url.
    """
    audio_url = None
    temp_path = None

    try:
        # ── Step 1: Download audio bytes from WhatsApp ─
        logger.info("voice_note: downloading audio media_id={}", media_id)
        audio_bytes = await whatsapp_service.download_media(media_id)

        if len(audio_bytes) > MAX_AUDIO_SIZE:
            logger.warning("voice_note: audio too large ({} bytes), skipping", len(audio_bytes))
            return VoiceNoteResult(text=None, audio_url=None)

        # ── Step 2: Write to temp file (needed by both Cloudinary and Whisper) ──
        # WhatsApp voice notes are OGG/Opus format
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        # ── Step 3: Upload to Cloudinary for dashboard playback ──
        # resource_type="video" handles both audio and video in Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(
                temp_path,
                resource_type="video",
                folder="whatsapp/voice_notes",
            )
            audio_url = upload_result.get("secure_url")
            logger.info("voice_note: uploaded to Cloudinary — {}", audio_url)
        except Exception as exc:
            logger.error("voice_note: Cloudinary upload failed — {}", exc)

        # ── Step 4: Send to Whisper for transcription ──
        # The prompt parameter primes Whisper with the expected language style.
        # This prevents Whisper from "correcting" Pidgin into broken English.
        # It also helps with Yoruba, Igbo, Hausa, and code-switching.
        logger.info("voice_note: sending to Whisper ({} bytes)", len(audio_bytes))
        with open(temp_path, "rb") as audio_file:
            transcription = await _openai_client.audio.transcriptions.create(
                model=Config.OPENAI_WHISPER_MODEL,
                file=audio_file,
                prompt=(
                    "This is a Nigerian customer speaking. They may use Nigerian Pidgin English, "
                    "Yoruba, Igbo, Hausa, or mix languages. Pidgin examples: "
                    "'Omo, I no wan buy again', 'Abeg how much e be', 'E don tey wey I order', "
                    "'Wetin happen to my order', 'I wan talk to person'. "
                    "Transcribe exactly as spoken, do not correct to standard English."
                ),
            )

        text = transcription.text.strip()

        if not text:
            logger.warning("voice_note: Whisper returned empty transcription")
            return VoiceNoteResult(text=None, audio_url=audio_url)

        logger.info("voice_note: transcribed ({} chars) — '{}'", len(text), text[:300])
        return VoiceNoteResult(text=text, audio_url=audio_url)

    except Exception as exc:
        logger.error("voice_note: failed — {}", exc)
        return VoiceNoteResult(text=None, audio_url=audio_url)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


async def generate_and_send_ai_voice_reply(
    db: AsyncSession,
    text: str,
    customer_phone: str,
    conversation_id: str,
) -> bool:
    """Convert AI text reply to a voice note via OpenAI TTS and send it to the customer.

    Returns True if the voice note was sent successfully, False otherwise.
    Caller should fall back to a plain text message on False.
    """
    temp_path = None
    try:
        logger.info("ai_tts: generating voice note ({} chars) for {}", len(text), customer_phone)

        response = await _openai_client.audio.speech.create(
            model=Config.OPENAI_TTS_MODEL,
            voice=Config.OPENAI_TTS_VOICE,
            input=text,
        )
        audio_bytes = response.content

        # ── Write to temp file for Cloudinary upload ──
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        # ── Upload to Cloudinary so the dashboard can play it back ──
        try:
            upload_result = cloudinary.uploader.upload(
                temp_path,
                resource_type="video",
                folder="whatsapp/ai_voice_replies",
            )
            audio_url = upload_result.get("secure_url")
            logger.info("ai_tts: uploaded to Cloudinary — {}", audio_url)
        except Exception as exc:
            logger.error("ai_tts: Cloudinary upload failed — {}", exc)
            # Still try to send using raw bytes fallback via a data URL — not ideal;
            # just bail and let caller fall back to text.
            return False

        # ── Send via WhatsApp ──
        result = await whatsapp_service.send_audio(to=customer_phone, audio_url=audio_url)
        message_id = result.get("message_id")
        logger.info("ai_tts: voice note sent — msg_id={}", message_id)

        # ── Log in messages table ──
        await message_service.create_message(
            db,
            MessageSchema(
                conversation_id=conversation_id,
                sender_type=utils.MessageSenderType.AI.value,
                direction=utils.MessageDirection.OUTBOUND.value,
                message_type=utils.MessageType.AUDIO.value,
                content=text,          # store the original text for dashboard display
                media_urls=[audio_url],
                whatsapp_message_id=message_id,
                status=utils.MessageStatus.SENT.value,
            ),
        )
        return True

    except Exception as exc:
        logger.error("ai_tts: failed — {}", exc)
        return False

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


# ── Allowed audio formats for staff uploads ──
ALLOWED_AUDIO_EXTENSIONS = (".ogg", ".mp3", ".m4a", ".wav", ".aac", ".amr")


async def send_staff_voice_note(
    db: AsyncSession,
    file_bytes: bytes,
    filename: str,
    customer_phone: str,
    conversation_id: str,
    caption: str | None = None,
) -> dict:
    """Upload an audio file to Cloudinary, send it to a customer via WhatsApp,
    and log the message in the conversation.

    Args:
        db: Database session.
        file_bytes: Raw audio file bytes.
        filename: Original filename (used to validate extension).
        customer_phone: Customer's WhatsApp number.
        conversation_id: Conversation ID to log the message under.
        caption: Optional follow-up text message.

    Returns:
        Dict with audio_url, message_id, and status.
    """

    # Validate file type
    lower_name = (filename or "").lower()
    if not any(lower_name.endswith(ext) for ext in ALLOWED_AUDIO_EXTENSIONS):
        raise exceptions.BadRequestException(
            f"Unsupported audio format. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
        )

    if not file_bytes:
        raise exceptions.BadRequestException("Audio file is empty.")

    # Upload to Cloudinary
    try:
        upload_result = cloudinary.uploader.upload(
            file_bytes,
            resource_type="video",
            folder="whatsapp/voice_notes",
        )
        audio_url = upload_result.get("secure_url")
        logger.info("send_staff_voice_note: uploaded to Cloudinary — {}", audio_url)
    except Exception as exc:
        logger.error("send_staff_voice_note: Cloudinary upload failed — {}", exc)
        raise exceptions.InternalServerException("Failed to upload audio file.")

    # Send via WhatsApp
    result = await whatsapp_service.send_audio(
        to=customer_phone,
        audio_url=audio_url,
        caption=caption,
    )

    logger.info("send_staff_voice_note: sent to {} — msg_id={}", customer_phone, result.get("message_id"))

    # Log the message in the conversation
    await message_service.create_message(
        db,
        MessageSchema(
            conversation_id=conversation_id,
            message_type=utils.MessageType.AUDIO.value,
            direction=utils.MessageDirection.OUTBOUND.value,
            media_urls=[audio_url],
            whatsapp_message_id=result.get("message_id"),
        ),
    )

    return {
        "status": "sent",
        "audio_url": audio_url,
        "message_id": result.get("message_id"),
    }
