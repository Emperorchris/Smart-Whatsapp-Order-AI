import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import exceptions
from ..core.config import Config
from ..core import utils
from ..db.model import customer_model, staff_model

logger = logging.getLogger(__name__)

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


def _normalize_phone(number: str) -> str:
    """Strip any 'whatsapp:' prefix and leading/trailing whitespace so we get a
    pure E.164 number (e.g. '2348012345678')."""
    value = number.strip()
    if value.lower().startswith("whatsapp:"):
        value = value.split(":", 1)[1].strip()
    # Remove any leading '+' — Meta expects digits only
    return value.lstrip("+")


async def send_message(to: str, body: str, media_urls: list[str] | None = None) -> dict[str, Any]:
    if not body or not body.strip():
        raise exceptions.BadRequestException("Message body cannot be empty.")

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
                resp = await _http_client.post(META_API_BASE, headers=headers, json=media_payload)
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
        resp = await _http_client.post(META_API_BASE, headers=headers, json=text_payload)
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


async def send_product_message(to: str, caption: str, media_urls: list[str]) -> dict[str, Any]:
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
                resp = await _http_client.post(META_API_BASE, headers=headers, json=payload)
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
                resp = await _http_client.post(META_API_BASE, headers=headers, json=text_payload)
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
        resp = await _http_client.post(META_API_BASE, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("Failed to send interactive buttons: %s", exc)
        raise exceptions.BadRequestException("Failed to send interactive message.", error_detail=str(exc))

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
        raise exceptions.BadRequestException("Failed to send interactive message.", error_detail=str(exc))

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


async def identify_sender(phone: str, db: AsyncSession) -> str:
    if not phone or not phone.strip():
        raise exceptions.BadRequestException("Sender phone number is required.")

    phone_value = phone.strip()
    if phone_value.lower().startswith("whatsapp:"):
        phone_value = phone_value.split(":", 1)[1]

    result = await db.execute(
        select(staff_model.Staff).filter(
            staff_model.Staff.is_active.is_(True),
            staff_model.Staff.whatsapp_number.is_not(None),
            staff_model.Staff.whatsapp_number == phone_value,
        )
    )
    staff = result.scalars().all()

    if staff:
        return utils.MessageSenderType.STAFF.value

    result = await db.execute(
        select(customer_model.Customer).filter(
            customer_model.Customer.whatsapp_number == phone_value
        )
    )
    customer = result.scalars().all()
    if customer:
        return utils.MessageSenderType.CUSTOMER.value

    raise exceptions.NotFoundException("Sender is not a registered customer or staff member.")


async def notify_all_staff(db: AsyncSession, message: str, customer_id: str | None = None) -> dict[str, Any]:
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

    sent_count = 0
    failed: list[dict[str, str]] = []

    for member in recipients:
        try:
            await send_message(to=member.whatsapp_number, body=full_message)
            sent_count += 1
        except Exception as exc:
            failed.append({"staff_id": str(member.id), "staff_name": member.name, "error": str(exc)})

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
