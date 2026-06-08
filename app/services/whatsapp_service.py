from typing import Any

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import exceptions
from ..core.config import Config
from ..core import utils
from ..db.model import customer_model, staff_model

# ──────────────────────────────────────────────────────────────
# Meta WhatsApp Cloud API implementation
# ──────────────────────────────────────────────────────────────

META_API_BASE = (
    f"https://graph.facebook.com/{Config.META_WHATSAPP_API_VERSION}"
    f"/{Config.META_WHATSAPP_PHONE_NUMBER_ID}/messages"
)

# Shared HTTP client — reuses TCP connections instead of opening a new one per request
_http_client = httpx.AsyncClient(timeout=30)


def _meta_headers() -> dict[str, str]:
    token = Config.META_WHATSAPP_ACCESS_TOKEN
    if not token:
        raise exceptions.InternalServerException(
            "Meta WhatsApp access token is not configured. Set META_WHATSAPP_ACCESS_TOKEN."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def normalize_phone(number: str) -> str:
    """Normalize a phone number to E.164 digits for the Meta API.
    Handles: +234..., 234..., 0803..., 803..., whatsapp:+234..."""
    value = number.strip()
    if value.lower().startswith("whatsapp:"):
        value = value.split(":", 1)[1].strip()
    value = value.lstrip("+")
    # Convert local Nigerian format to international
    if value.startswith("0") and len(value) >= 10:
        value = "234" + value[1:]
    elif not value.startswith("234") and len(value) >= 9:
        value = "234" + value
    return value


# Keep private alias for internal use
_normalize_phone = normalize_phone


async def download_media(media_id: str) -> bytes:
    """Download media (voice note, image, etc.) from WhatsApp by media ID.

    WhatsApp media download is a 2-step process:
      1. GET /media_id → returns a JSON with the download URL
      2. GET download_url → returns the actual file bytes

    Both calls need the Meta access token for authentication.
    """
    headers = _meta_headers()
    api_base = f"https://graph.facebook.com/{Config.META_WHATSAPP_API_VERSION}"

    # Step 1: Get the download URL from WhatsApp
    url_resp = await _http_client.get(f"{api_base}/{media_id}", headers=headers)
    if url_resp.status_code != 200:
        logger.error("download_media: failed to get URL for media_id={} — {}", media_id, url_resp.text)
        raise exceptions.InternalServerException("Failed to retrieve media URL from WhatsApp.")

    download_url = url_resp.json().get("url")
    if not download_url:
        raise exceptions.InternalServerException("WhatsApp returned no download URL for media.")

    # Step 2: Download the actual file bytes
    # Note: Content-Type header must NOT be application/json for binary download
    download_headers = {"Authorization": headers["Authorization"]}
    file_resp = await _http_client.get(download_url, headers=download_headers)
    if file_resp.status_code != 200:
        logger.error("download_media: failed to download file — {}", file_resp.status_code)
        raise exceptions.InternalServerException("Failed to download media file from WhatsApp.")

    logger.info("download_media: downloaded {} bytes for media_id={}", len(file_resp.content), media_id)
    return file_resp.content


async def send_message(
    to: str, body: str, media_urls: list[str] | None = None
) -> dict[str, Any]:
    """Send a text message (and optional media) to a WhatsApp number via the Meta Cloud API."""
    if not body or not body.strip():
        raise exceptions.BadRequestException("Message body cannot be empty.")

    # WhatsApp text message limit is 4096 characters
    if len(body) > 4096:
        body = body[:4093] + "..."

    phone = _normalize_phone(to)
    headers = _meta_headers()

    sent_media_ids: list[str] = []

    # Send media first (each as a separate message — Meta supports 1 media per message)
    if media_urls:
        for url in media_urls:
            media_type = _detect_media_type(url)
            media_payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": media_type,
                media_type: {
                    "link": url,
                },
            }
            try:
                resp = await _http_client.post(
                    META_API_BASE, headers=headers, json=media_payload
                )
                resp.raise_for_status()
                data = resp.json()
                msg_id = data.get("messages", [{}])[0].get("id")
                if msg_id:
                    sent_media_ids.append(msg_id)
            except httpx.HTTPError as exc:
                logger.warning("Failed to send media %s: %s", url, exc)

    # Send the text message
    text_payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": body.strip()},
    }

    try:
        resp = await _http_client.post(
            META_API_BASE, headers=headers, json=text_payload
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("Failed to send WhatsApp message: %s", exc)
        raise exceptions.BadRequestException(
            "Failed to send WhatsApp message.", error_detail=str(exc)
        )

    message_id = data.get("messages", [{}])[0].get("id")

    return {
        "message_id": message_id,
        "status": "sent",
        "to": phone,
        "media_ids": sent_media_ids,
    }


async def send_audio(to: str, audio_url: str, caption: str | None = None) -> dict[str, Any]:
    """Send an audio file to a WhatsApp number.

    Args:
        to: Recipient phone number.
        audio_url: Public URL of the audio file (e.g. Cloudinary URL).
        caption: Optional text caption (not supported by WhatsApp audio — ignored by API,
                 but we send as a follow-up text if provided).
    """
    phone = _normalize_phone(to)
    headers = _meta_headers()

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "audio",
        "audio": {"link": audio_url},
    }

    try:
        resp = await _http_client.post(META_API_BASE, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("send_audio: failed — {}", exc)
        raise exceptions.BadRequestException("Failed to send audio message.")

    message_id = data.get("messages", [{}])[0].get("id")
    logger.info("send_audio: sent to {} — msg_id={}", phone, message_id)

    # WhatsApp audio messages don't support captions, so send as follow-up text
    if caption and caption.strip():
        await send_message(to=to, body=caption)

    return {"message_id": message_id, "status": "sent", "to": phone}


async def send_product_message(
    to: str, caption: str, media_urls: list[str]
) -> dict[str, Any]:
    """Send product media with caption.
    - Single media: sends as image/video with caption attached (one neat bubble).
    - Multiple media: sends all plain first, then caption as separate text."""
    phone = _normalize_phone(to)
    headers = _meta_headers()
    sent_ids: list[str] = []

    if len(media_urls) == 1:
        # Single media — attach caption directly for a clean single bubble
        url = media_urls[0]
        media_type = _detect_media_type(url)
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": media_type,
            media_type: {"link": url},
        }
        if caption:
            payload[media_type]["caption"] = caption.strip()

        try:
            resp = await _http_client.post(META_API_BASE, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            msg_id = data.get("messages", [{}])[0].get("id")
            if msg_id:
                sent_ids.append(msg_id)
        except httpx.HTTPError as exc:
            logger.warning("Failed to send product media %s: %s", url, exc)

    else:
        # Multiple media — send all plain, then caption as text
        for url in media_urls:
            media_type = _detect_media_type(url)
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": media_type,
                media_type: {"link": url},
            }
            try:
                resp = await _http_client.post(
                    META_API_BASE, headers=headers, json=payload
                )
                resp.raise_for_status()
                data = resp.json()
                msg_id = data.get("messages", [{}])[0].get("id")
                if msg_id:
                    sent_ids.append(msg_id)
            except httpx.HTTPError as exc:
                logger.warning("Failed to send product media %s: %s", url, exc)

        if caption:
            text_payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": caption.strip()},
            }
            try:
                resp = await _http_client.post(
                    META_API_BASE, headers=headers, json=text_payload
                )
                resp.raise_for_status()
                data = resp.json()
                msg_id = data.get("messages", [{}])[0].get("id")
                if msg_id:
                    sent_ids.append(msg_id)
            except httpx.HTTPError as exc:
                logger.warning("Failed to send product caption: %s", exc)

    return {"status": "sent", "to": phone, "media_ids": sent_ids}


async def send_interactive_buttons(
    to: str,
    body: str,
    buttons: list[dict[str, str]],
    header: str = "",
    footer: str = "",
) -> dict[str, Any]:
    """Send an interactive button message (max 3 buttons).
    buttons: [{"id": "btn_home", "title": "Home"}, ...]"""

    phone = _normalize_phone(to)
    headers = _meta_headers()

    action_buttons = [
        {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"]}}
        for btn in buttons[:3]
    ]

    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": action_buttons},
        },
    }

    if header:
        payload["interactive"]["header"] = {"type": "text", "text": header}
    if footer:
        payload["interactive"]["footer"] = {"text": footer}

    try:
        logger.info(
            "send_interactive_buttons: POST to {} for phone {}", META_API_BASE, phone
        )
        logger.debug("send_interactive_buttons: payload={}", payload)
        resp = await _http_client.post(META_API_BASE, headers=headers, json=payload)
        logger.info(
            "send_interactive_buttons: HTTP {} response={}", resp.status_code, resp.text
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("send_interactive_buttons: FAILED for {}: {}", phone, exc)
        raise exceptions.BadRequestException(
            "Failed to send interactive message.", error_detail=str(exc)
        )

    message_id = data.get("messages", [{}])[0].get("id")
    return {"message_id": message_id, "status": "sent", "to": phone}


async def send_interactive_list(
    to: str,
    body: str,
    button_text: str,
    sections: list[dict[str, Any]],
    header: str = "",
    footer: str = "",
) -> dict[str, Any]:
    """Send an interactive list message.
    sections: [{"title": "Section", "rows": [{"id": "row_1", "title": "Option 1", "description": "..."}]}]"""

    phone = _normalize_phone(to)
    headers = _meta_headers()

    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button_text,
                "sections": sections,
            },
        },
    }

    if header:
        payload["interactive"]["header"] = {"type": "text", "text": header}
    if footer:
        payload["interactive"]["footer"] = {"text": footer}

    try:
        resp = await _http_client.post(META_API_BASE, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("Failed to send interactive list: %s", exc)
        raise exceptions.BadRequestException(
            "Failed to send interactive message.", error_detail=str(exc)
        )

    message_id = data.get("messages", [{}])[0].get("id")
    return {"message_id": message_id, "status": "sent", "to": phone}


def _detect_media_type(url: str) -> str:
    """Guess media type from URL extension. Defaults to 'image'."""
    lower = url.lower()
    if any(ext in lower for ext in [".mp4", ".mov", ".avi", ".3gp"]):
        return "video"
    if any(ext in lower for ext in [".mp3", ".ogg", ".amr", ".aac"]):
        return "audio"
    if any(ext in lower for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx"]):
        return "document"
    return "image"


async def identify_staff_by_phone(db: AsyncSession, phone: str):
    """Find a staff member by phone number using all format variants."""
    phone_value = phone.strip().lstrip("+")
    phone_variants = {phone_value, "+" + phone_value}
    if phone_value.startswith("234") and len(phone_value) > 10:
        local = phone_value[3:]
        phone_variants.update({local, "0" + local, "+234" + local})
    elif phone_value.startswith("0") and len(phone_value) >= 10:
        without_zero = phone_value[1:]
        phone_variants.update(
            {without_zero, "234" + without_zero, "+234" + without_zero}
        )
    elif len(phone_value) >= 9:
        phone_variants.update(
            {"0" + phone_value, "234" + phone_value, "+234" + phone_value}
        )

    result = await db.execute(
        select(staff_model.Staff).filter(
            staff_model.Staff.is_active.is_(True),
            staff_model.Staff.whatsapp_number.in_(phone_variants),
        )
    )
    return result.scalars().first()


async def identify_sender(phone: str, db: AsyncSession) -> str:
    if not phone or not phone.strip():
        raise exceptions.BadRequestException("Sender phone number is required.")

    phone_value = phone.strip()
    if phone_value.lower().startswith("whatsapp:"):
        phone_value = phone_value.split(":", 1)[1]
    phone_value = phone_value.lstrip("+")

    # Build all possible phone formats to match against DB
    # Handles: 2347039487884, +2347039487884, 07039487884, 7039487884
    phone_variants = {phone_value, "+" + phone_value}

    if phone_value.startswith("234") and len(phone_value) > 10:
        local = phone_value[3:]
        phone_variants.add(local)
        phone_variants.add("0" + local)
        phone_variants.add("+234" + local)
    elif phone_value.startswith("0") and len(phone_value) >= 10:
        without_zero = phone_value[1:]
        phone_variants.add(without_zero)
        phone_variants.add("234" + without_zero)
        phone_variants.add("+234" + without_zero)
    elif len(phone_value) >= 9:
        phone_variants.add("0" + phone_value)
        phone_variants.add("234" + phone_value)
        phone_variants.add("+234" + phone_value)

    result = await db.execute(
        select(staff_model.Staff).filter(
            staff_model.Staff.is_active.is_(True),
            staff_model.Staff.whatsapp_number.is_not(None),
            staff_model.Staff.whatsapp_number.in_(phone_variants),
        )
    )
    staff = result.scalars().first()

    if staff:
        return utils.MessageSenderType.STAFF.value

    result = await db.execute(
        select(customer_model.Customer).filter(
            customer_model.Customer.whatsapp_number.in_(phone_variants)
        )
    )
    customer = result.scalars().first()
    if customer:
        return utils.MessageSenderType.CUSTOMER.value

    raise exceptions.NotFoundException(
        "Sender is not a registered customer or staff member."
    )


async def notify_all_staff(
    db: AsyncSession,
    message: str,
    customer_id: str | None = None,
    handoff_id: str | None = None,
) -> dict[str, Any]:
    if not message or not message.strip():
        raise exceptions.BadRequestException("Notification message cannot be empty.")

    full_message = message.strip()
    if customer_id:
        result = await db.execute(
            select(customer_model.Customer).filter(
                customer_model.Customer.id == customer_id
            )
        )
        customer = result.scalars().first()
        if customer:
            full_message += (
                f"\n\n👤 *Customer Details*"
                f"\nName: {customer.name}"
                f"\nWhatsApp: {customer.whatsapp_number}"
                f"\nSegment: {customer.customer_segment or 'N/A'}"
                f"\nStatus: {customer.customer_status}"
            )
            if customer.email:
                full_message += f"\nEmail: {customer.email}"

    result = await db.execute(
        select(staff_model.Staff).filter(
            staff_model.Staff.is_active.is_(True),
            staff_model.Staff.whatsapp_number.is_not(None),
        )
    )
    recipients = result.scalars().all()
    logger.info(
        "notify_all_staff: found {} active staff with whatsapp numbers", len(recipients)
    )
    for r in recipients:
        logger.info(
            "notify_all_staff: staff '{}' → raw number '{}'", r.name, r.whatsapp_number
        )

    sent_count = 0
    failed: list[dict[str, str]] = []

    for member in recipients:
        try:
            normalized = _normalize_phone(member.whatsapp_number)
            logger.info(
                "notify_all_staff: sending to '{}' (normalized: '{}')",
                member.whatsapp_number,
                normalized,
            )
            if handoff_id:
                handoff_short_id = str(handoff_id)[:8]
                resp = await send_interactive_buttons(
                    to=member.whatsapp_number,
                    body=full_message,
                    buttons=[
                        {
                            "id": f"claim_cust_{handoff_short_id}",
                            "title": "Claim → Customer",
                        },
                        {"id": f"claim_ai_{handoff_short_id}", "title": "Claim → AI"},
                    ],
                    header="New Handoff Request",
                )
                logger.info(
                    "notify_all_staff: interactive buttons sent to '{}', response: {}",
                    normalized,
                    resp,
                )
            else:
                resp = await send_message(to=member.whatsapp_number, body=full_message)
                logger.info(
                    "notify_all_staff: message sent to '{}', response: {}",
                    normalized,
                    resp,
                )
            sent_count += 1
        except Exception as exc:
            logger.error(
                "notify_all_staff: FAILED to send to '{}': {}",
                member.whatsapp_number,
                exc,
            )
            failed.append(
                {
                    "staff_id": str(member.id),
                    "staff_name": member.name,
                    "error": str(exc),
                }
            )

    logger.info("notify_all_staff: done — sent={}, failed={}", sent_count, len(failed))
    return {
        "total_recipients": len(recipients),
        "sent_count": sent_count,
        "failed_count": len(failed),
        "failed": failed,
    }


# ──────────────────────────────────────────────────────────────
# Twilio implementation (commented out — kept for reference)
# ──────────────────────────────────────────────────────────────

# import os
# from twilio.base.exceptions import TwilioRestException
# from twilio.rest import Client
#
#
# def _format_twilio_whatsapp(number: str) -> str:
# 	if not number or not number.strip():
# 		raise exceptions.BadRequestException("A valid WhatsApp number is required.")
#
# 	value = number.strip()
# 	if value.lower().startswith("whatsapp:"):
# 		return value
#
# 	return f"whatsapp:{value}"
#
#
# def _get_twilio_client() -> Client:
# 	account_sid = Config.TWILIO_ACCOUNT_SID or os.getenv("TWILIO_ACCOUNT_SID")
# 	auth_token = Config.TWILIO_AUTH_TOKEN or os.getenv("TWILIO_AUTH_TOKEN")
#
# 	if not account_sid or not auth_token:
# 		raise exceptions.InternalServerException(
# 			"Twilio credentials are not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
# 		)
#
# 	return Client(account_sid, auth_token)
