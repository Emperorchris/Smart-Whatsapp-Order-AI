import re

# import logging
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

from ..core import utils
from ..db.schemas.message_schema import MessageSchema
from ..ai.graph import agent_graph
from ..ai.memory.conversation_memory import (
    load_conversation_history,
    save_agent_messages,
    _extract_text_content,
)
from .whatsapp_webhook_processing_service import IncomingWhatsAppPayload
from ..db.schemas.customers_schema import CustomerResponse
from ..db.schemas.conversation_schema import ConversationResponse
from . import (
    message_service,
    whatsapp_service,
    whatsapp_webhook_processing_service,
    conversation_service,
)
from . import staff_service, voice_note_service
from .whatsapp_staff_webhook_service import _get_staff_mode


# logger = logging.getLogger(__name__)


async def process_customer_message(
    db: AsyncSession,
    payload: IncomingWhatsAppPayload,
    customer: CustomerResponse,
    active_conversation: ConversationResponse,
    sender_type: str = utils.MessageSenderType.CUSTOMER.value,
):
    """Process a single customer message: resolve context, run the AI agent, and send the reply."""

    # ── Voice note handling ──
    customer_sent_voice_note = False
    if payload.message_type == "audio" and payload.media_urls:
        audio_media_id = payload.media_urls[0]
        logger.info("process_message: voice note detected, media_id={}", audio_media_id)

        result = await voice_note_service.transcribe_voice_note(audio_media_id)

        if result.text:
            # Replace empty body with transcribed text
            payload.body = result.text
            customer_sent_voice_note = True
            logger.info("process_message: transcribed voice note — '{}'", result.text[:100])
        else:
            # Transcription failed — ask customer to retry or type
            await whatsapp_service.send_message(
                to=payload.sender_number,
                body="I couldn't catch that clearly. Could you type your message or send another voice note?",
            )
            return

        # Store the Cloudinary audio URL in media_urls so it's saved in the message record
        if result.audio_url:
            payload.media_urls = [result.audio_url]

    # Handle interactive address selection from checkout flow
    if payload.interactive_id:
        if payload.interactive_id.startswith("addr_select_"):
            addr_id = payload.interactive_id[len("addr_select_") :]
            if addr_id == "new":
                payload.body = f"[Customer wants to add a new delivery address]"
            else:
                payload.body = f'[Customer selected saved address with ID: {addr_id}. Call place_order with customer_address_id="{addr_id}"]'
        elif payload.interactive_id.startswith("chgaddr|"):
            # Format: chgaddr|{order_number} — "Change Address" button on order confirmation
            order_number = payload.interactive_id.split("|")[1] if "|" in payload.interactive_id else ""
            payload.body = (
                f'[Customer wants to change delivery address for order {order_number}. '
                f'Call update_order_address with order_number="{order_number}" and NO other arguments. '
                f'Do NOT add items to cart or do anything else.]'
            )
        elif payload.interactive_id.startswith("addrchg|"):
            # Format: addrchg|{order_number}|{address_id_or_new}
            parts = payload.interactive_id.split("|")
            order_number = parts[1] if len(parts) > 1 else ""
            addr_id = parts[2] if len(parts) > 2 else ""
            if addr_id == "new":
                payload.body = (
                    f"[Customer wants to add a new delivery address for order {order_number}. "
                    f"After saving the address with save_delivery_address, you MUST call "
                    f'update_order_address with order_number="{order_number}" and the new address ID.]'
                )
            else:
                payload.body = f'[Customer wants to change address for order {order_number}. Call update_order_address with order_number="{order_number}" and new_address_id="{addr_id}"]'
        elif payload.interactive_id.startswith("cancel|"):
            order_number = payload.interactive_id.split("|")[1] if "|" in payload.interactive_id else ""
            payload.body = f'[Customer wants to cancel order {order_number}. Call cancel_order with order_number="{order_number}". Do NOT do anything else.]'
        elif payload.interactive_id.startswith("track|"):
            order_number = payload.interactive_id.split("|")[1] if "|" in payload.interactive_id else ""
            payload.body = f'[Customer wants to track order {order_number}. Call check_order_status with order_number="{order_number}".]'
        elif payload.interactive_id.startswith("products_page_"):
            page = payload.interactive_id[len("products_page_"):]
            payload.body = f'[Customer tapped "Show More" for product list. Call list_product_names with page={page}.]'
        elif payload.interactive_id.startswith("addr_label_"):
            label = payload.interactive_id[len("addr_label_") :]
            payload.body = f"[Customer selected address type: {label}. Ask for their full address details: street, city, state, landmark.]"

    # If the user replied to a specific message, resolve what they're referring to
    reply_context = await whatsapp_webhook_processing_service.resolve_reply_context(
        db, payload.reply_to_message_id
    )
    if reply_context:
        payload.body = (
            f'[Customer replied to this message: "{reply_context}"]\n\n{payload.body}'
        )

    # Log inbound message
    await whatsapp_webhook_processing_service.log_inbound_message(
        db,
        active_conversation.id,
        utils.MessageDirection.INBOUND.value,
        payload,
    )

    # Re-check handoff status from DB (the object may be stale in background tasks)
    fresh_conversation = await conversation_service.get_conversation_by_id(
        db, str(active_conversation.id)
    )
    if (
        fresh_conversation.handoff_to_human
        and fresh_conversation.handoff_status == utils.HandOffStatus.ACTIVE.value
    ):
        # Forward customer message to the assigned staff member
        if fresh_conversation.assigned_staff_id:
            try:
                staff = await staff_service.get_staff_by_id(
                    db, str(fresh_conversation.assigned_staff_id)
                )
                if staff and staff.whatsapp_number:
                    customer_name = payload.profile_name or "Customer"
                    current_mode = _get_staff_mode(str(staff.id))
                    # If customer sent a voice note, forward the audio + transcription
                    if payload.message_type == "audio" and payload.media_urls:
                        await whatsapp_service.send_audio(
                            to=staff.whatsapp_number,
                            audio_url=payload.media_urls[0],
                        )

                    # Send customer message as interactive buttons so staff can act immediately
                    forward_body = payload.body[:1024] if payload.body else "[Voice note — listen above]"
                    await whatsapp_service.send_interactive_buttons(
                        to=staff.whatsapp_number,
                        header=f"{customer_name} says:",
                        body=forward_body,
                        buttons=[
                            {"id": "staff_mode_ai", "title": "Talk to AI"},
                            {"id": "staff_cmd_done", "title": "Done"},
                            {"id": "staff_cmd_skip", "title": "Skip"},
                        ]
                        if current_mode == "customer"
                        else [
                            {"id": "staff_mode_customer", "title": "Talk to Customer"},
                            {"id": "staff_cmd_done", "title": "Done"},
                            {"id": "staff_cmd_info", "title": "Info"},
                        ],
                    )
            except Exception as exc:
                logger.error("Failed to forward customer message to staff: {}", exc)
        return

    # Run the LangGraph agent
    history = await load_conversation_history(db, str(active_conversation.id))
    initial_state = {
        "messages": history,
        "customer_whatsapp_number": payload.sender_number,
        "customer_name": payload.profile_name,
        "customer_display_name": payload.profile_name,
        "customer_wa_id": payload.wa_id,
        "customer_id": str(customer.id),
        "conversation_id": str(active_conversation.id),
        "sender_type": sender_type,
    }

    history_count = len(initial_state["messages"])

    result = await agent_graph.run_agent(
        initial_state,
        db=db,
        customer_id=str(customer.id),
        conversation_id=str(active_conversation.id),
    )

    # OpenAI returns content as str, Claude returns list of blocks
    # ai_reply = (
    #     result["messages"][-1].content
    #     if result["messages"]
    #     else "Sorry, I couldn't process your request right now."
    # )
    raw_content = result["messages"][-1].content if result["messages"] else None
    ai_reply = (
        _extract_text_content(raw_content)
        if raw_content
        else "Sorry, I couldn't process your request right now."
    )

    # Only scan NEW messages from this agent run (not loaded history)
    new_messages = result["messages"][history_count:]

    await save_agent_messages(db, str(active_conversation.id), new_messages)

    # Extract per-product blocks from new messages (ToolMessages have product data)
    product_blocks = _extract_product_blocks(new_messages)

    # Clean all product/media blocks from the final AI reply
    ai_reply = re.sub(
        r"\[PRODUCT_START\].*?\[PRODUCT_END\]", "", ai_reply, flags=re.DOTALL
    )
    ai_reply = re.sub(r"\n*\[PRODUCT_MEDIA\].*?\[/PRODUCT_MEDIA\]", "", ai_reply)
    ai_reply = re.sub(r"\n*\[MEDIA_URLS\].*?\[/MEDIA_URLS\]", "", ai_reply)
    ai_reply = ai_reply.strip()

    # Suppress AI text when a tool already sent an interactive WhatsApp message
    # (e.g. address picker, saved address list). Sending text on top confuses the customer.
    if any(
        "[INTERACTIVE_SENT]" in str(m.content)
        for m in new_messages
        if hasattr(m, "content")
    ):
        logger.info("process_customer_message: suppressing AI text — interactive already sent by tool")
        ai_reply = ""

    # If there are product blocks, merge the AI follow-up into the last block's caption
    # so the customer sees one message instead of a duplicate
    if product_blocks and ai_reply:
        last_text, last_media = product_blocks[-1]
        product_blocks[-1] = (f"{last_text}\n\n{ai_reply}", last_media)
        ai_reply = ""

    await _send_reply(db, payload, active_conversation, ai_reply, product_blocks, customer_sent_voice_note)


async def _send_reply(
    db: AsyncSession,
    payload: IncomingWhatsAppPayload,
    active_conversation: ConversationResponse,
    ai_reply: str,
    product_blocks: list[tuple[str, list[str]]],
    reply_with_voice: bool = False,
):
    """Send the AI reply (with product media if any) back to the customer via WhatsApp.

    If reply_with_voice is True (customer sent a voice note), the plain-text AI reply
    is converted to a voice note via TTS. Product blocks are always sent as text/media.
    """
    try:
        if product_blocks:
            # Send product blocks sequentially to preserve display order
            for block_text, block_media in product_blocks:
                try:
                    if block_media:
                        result_msg = await whatsapp_service.send_product_message(
                            to=payload.sender_number,
                            caption=block_text,
                            media_urls=block_media,
                        )
                    else:
                        result_msg = await whatsapp_service.send_message(
                            to=payload.sender_number,
                            body=block_text,
                        )
                    wamid = (
                        result_msg.get("message_id")
                        or (result_msg.get("media_ids") or [None])[-1]
                    )
                    if wamid:
                        await message_service.create_message(
                            db,
                            MessageSchema(
                                conversation_id=active_conversation.id,
                                sender_type=utils.MessageSenderType.AI.value,
                                direction=utils.MessageDirection.OUTBOUND.value,
                                message_type=utils.MessageType.TEXT.value,
                                content=block_text,
                                whatsapp_message_id=wamid,
                                status=utils.MessageStatus.SENT.value,
                            ),
                        )
                except Exception as exc:
                    logger.warning("Failed to send product block: %s", exc)

            if ai_reply:
                await _dispatch_text_or_voice(db, payload, active_conversation, ai_reply, reply_with_voice)
        else:
            if ai_reply:
                await _dispatch_text_or_voice(db, payload, active_conversation, ai_reply, reply_with_voice)
    except Exception as exc:
        logger.error("Failed to send reply to %s: %s", payload.sender_number, exc)


async def _dispatch_text_or_voice(
    db: AsyncSession,
    payload: IncomingWhatsAppPayload,
    active_conversation: ConversationResponse,
    text: str,
    as_voice: bool,
):
    """Send text as a voice note (TTS) if as_voice=True, otherwise send as plain text.
    Falls back to plain text if TTS fails."""
    if as_voice:
        sent = await voice_note_service.generate_and_send_ai_voice_reply(
            db=db,
            text=text,
            customer_phone=payload.sender_number,
            conversation_id=str(active_conversation.id),
        )
        if sent:
            return
        logger.warning("_dispatch_text_or_voice: TTS failed, falling back to text reply")

    # Plain text path (also fallback when TTS fails)
    result_msg = await whatsapp_service.send_message(to=payload.sender_number, body=text)
    await message_service.create_message(
        db,
        MessageSchema(
            conversation_id=active_conversation.id,
            sender_type=utils.MessageSenderType.AI.value,
            direction=utils.MessageDirection.OUTBOUND.value,
            message_type=utils.MessageType.TEXT.value,
            content=text,
            whatsapp_message_id=result_msg.get("message_id"),
            status=utils.MessageStatus.SENT.value,
        ),
    )


def _extract_product_blocks(messages: list) -> list[tuple[str, list[str]]]:
    """Parse tool messages for [PRODUCT_START]...[PRODUCT_END] blocks.
    Returns a list of (product_text, [media_urls]) tuples."""
    blocks: list[tuple[str, list[str]]] = []

    for msg in messages:
        # ToolMessage content can be a string or list — normalize it
        raw = getattr(msg, "content", "") or ""
        if isinstance(raw, list):
            content = " ".join(str(item) for item in raw)
        else:
            content = str(raw)

        if "[PRODUCT_START]" not in content:
            continue

        # Find all product blocks in this message
        product_matches = re.findall(
            r"\[PRODUCT_START\]\s*(.*?)\s*\[PRODUCT_END\]", content, re.DOTALL
        )

        for block in product_matches:
            # Extract media URLs from this block
            media_match = re.search(r"\[PRODUCT_MEDIA\](.*?)\[/PRODUCT_MEDIA\]", block)
            media_urls = []
            if media_match:
                media_urls = [
                    u.strip() for u in media_match.group(1).split(",") if u.strip()
                ]

            # Clean the block text (remove media tags)
            clean_text = re.sub(
                r"\n*\[PRODUCT_MEDIA\].*?\[/PRODUCT_MEDIA\]", "", block
            ).strip()

            if clean_text:
                blocks.append((clean_text, media_urls))

    return blocks
