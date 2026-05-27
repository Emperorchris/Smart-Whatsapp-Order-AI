from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import exceptions, utils
from ..db.schemas.conversation_schema import ConversationSchema
from ..db.schemas.customers_schema import CustomerSchema
from ..db.schemas.message_schema import MessageSchema
from ..db.schemas.processed_webhook_schema import ProcessedWebhookSchema
from . import (
    conversation_service,
    customer_service,
    message_service,
    processed_webhook_service,
)


@dataclass
class IncomingWhatsAppPayload:
    sender_number: str
    body: str
    message_sid: str
    num_media: int
    media_urls: list[str]
    message_type: str
    profile_name: str | None
    wa_id: str | None
    reply_to_message_id: str | None = None
    interactive_id: str | None = None  # button/list reply ID (e.g. "handoff_resolve_yes")


def parse_incoming_payload(data: dict[str, Any]) -> IncomingWhatsAppPayload | None:
    try:
        entry = data.get("entry", [])
        if not entry:
            return None

        changes = entry[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})
        messages = value.get("messages")
        if not messages:
            return None

        msg = messages[0]
        contacts = value.get("contacts", [])
        contact = contacts[0] if contacts else {}

        sender_number = msg.get("from", "")
        message_id = msg.get("id", "")
        msg_type = msg.get("type", "text")
        wa_id = contact.get("wa_id", sender_number)
        profile_name = contact.get("profile", {}).get("name")

        context = msg.get("context", {})
        reply_to_message_id = context.get("id") if context else None

        body = ""
        media_urls = []
        num_media = 0
        interactive_id = None

        if msg_type == "text":
            body = msg.get("text", {}).get("body", "")

        elif msg_type in ("image", "video", "audio", "document"):
            media_obj = msg.get(msg_type, {})
            caption = media_obj.get("caption", "")
            body = caption
            media_id = media_obj.get("id", "")
            if media_id:
                media_urls = [media_id]
                num_media = 1

        elif msg_type == "sticker":
            body = "[Sticker]"

        elif msg_type == "location":
            loc = msg.get("location", {})
            body = f"[Location: {loc.get('latitude', '')}, {loc.get('longitude', '')}]"

        elif msg_type == "contacts":
            body = "[Contact card shared]"

        elif msg_type == "interactive":
            interactive = msg.get("interactive", {})
            interactive_type = interactive.get("type", "")
            if interactive_type == "button_reply":
                body = interactive.get("button_reply", {}).get("title", "")
                interactive_id = interactive.get("button_reply", {}).get("id", "")
            elif interactive_type == "list_reply":
                body = interactive.get("list_reply", {}).get("title", "")
                interactive_id = interactive.get("list_reply", {}).get("id", "")

        resolved_type = _resolve_meta_message_type(msg_type)

        return IncomingWhatsAppPayload(
            sender_number=sender_number,
            body=body,
            message_sid=message_id,
            num_media=num_media,
            media_urls=media_urls,
            message_type=resolved_type,
            profile_name=profile_name,
            wa_id=wa_id,
            reply_to_message_id=reply_to_message_id,
            interactive_id=interactive_id,
        )

    except (KeyError, IndexError):
        return None


def _resolve_meta_message_type(msg_type: str) -> str:
    mapping = {
        "text": utils.MessageType.TEXT.value,
        "image": utils.MessageType.IMAGE.value,
        "video": utils.MessageType.VIDEO.value,
        "audio": utils.MessageType.AUDIO.value,
        "document": utils.MessageType.DOCUMENT.value,
        "sticker": utils.MessageType.IMAGE.value,
        "location": utils.MessageType.TEXT.value,
        "contacts": utils.MessageType.TEXT.value,
        "interactive": utils.MessageType.TEXT.value,
    }
    return mapping.get(msg_type, utils.MessageType.TEXT.value)


async def resolve_reply_context(db: AsyncSession, reply_to_message_id: str | None) -> str | None:
    if not reply_to_message_id:
        return None

    from ..db.model.message_model import Message

    result = await db.execute(
        select(Message).filter(Message.whatsapp_message_id == reply_to_message_id)
    )
    original = result.scalars().first()

    if not original or not original.content:
        return None

    return original.content


async def ensure_not_duplicate_event(db: AsyncSession, message_sid: str) -> bool:
    event_id = f"message_{message_sid}"

    try:
        await processed_webhook_service.get_processed_webhook_by_event_id(db, event_id)
        return False
    except exceptions.NotFoundException:
        await processed_webhook_service.create_processed_webhook(
            db,
            ProcessedWebhookSchema(source="meta", event_id=event_id),
        )
        return True


async def get_or_create_customer(db: AsyncSession, payload: IncomingWhatsAppPayload):
    try:
        return await customer_service.get_customer_by_whatsapp_number(
            db, payload.sender_number
        )
    except exceptions.NotFoundException:
        name = payload.profile_name
        display_name = payload.profile_name or name

        return await customer_service.create_customer(
            db,
            CustomerSchema(
                name=name,
                whatsapp_number=payload.sender_number,
                display_name=display_name,
                extra_metadata={"wa_id": payload.wa_id} if payload.wa_id else None,
            ),
        )


async def get_or_create_active_conversation(db: AsyncSession, customer_id: str):
    conversations = await conversation_service.get_conversations_by_customer_id(
        db, customer_id
    )
    active_conversation = next(
        (
            c
            for c in conversations
            if str(c.status) == utils.ConversationStatus.ACTIVE.value
            or c.status == utils.ConversationStatus.ACTIVE
        ),
        None,
    )

    if active_conversation:
        return active_conversation

    return await conversation_service.create_conversation(
        db,
        ConversationSchema(customer_id=customer_id),
    )


async def log_inbound_message(
    db: AsyncSession,
    conversation_id: str,
    message_direction: str,
    payload: IncomingWhatsAppPayload,
) -> None:
    await message_service.create_message(
        db,
        MessageSchema(
            conversation_id=conversation_id,
            sender_type=utils.MessageSenderType.CUSTOMER.value,
            direction=message_direction,
            message_type=payload.message_type,
            content=payload.body,
            media_urls=payload.media_urls or None,
            status=utils.MessageStatus.DELIVERED.value,
            whatsapp_message_id=payload.message_sid,
        ),
    )


async def log_outbound_message(
    db: AsyncSession, conversation_id: str, content: str, media_urls: list[str] | None = None
) -> None:
    await message_service.create_message(
        db,
        MessageSchema(
            conversation_id=conversation_id,
            sender_type=utils.MessageSenderType.AI.value,
            direction=utils.MessageDirection.OUTBOUND.value,
            message_type=utils.MessageType.TEXT.value,
            content=content,
            media_urls=media_urls,
            status=utils.MessageStatus.SENT.value,
        ),
    )
