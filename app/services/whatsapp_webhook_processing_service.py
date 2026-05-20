from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy.orm import Session

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


def parse_incoming_payload(form: Mapping[str, Any]) -> IncomingWhatsAppPayload:
    sender_from = form.get("From", "")
    body = form.get("Body", "")
    message_sid = form.get("MessageSid", "")
    raw_num_media = form.get("NumMedia", "0")

    try:
        num_media = max(int(raw_num_media or 0), 0)
    except (TypeError, ValueError):
        num_media = 0

    sender_number = sender_from.replace("whatsapp:", "").strip()
    media_urls = [
        form.get(f"MediaUrl{i}") for i in range(num_media) if form.get(f"MediaUrl{i}")
    ]

    profile_name = (form.get("ProfileName") or "").strip() or None
    wa_id = (form.get("WaId") or "").strip() or None

    message_type = _resolve_message_type(form, num_media)

    return IncomingWhatsAppPayload(
        sender_number=sender_number,
        body=body,
        message_sid=message_sid,
        num_media=num_media,
        media_urls=media_urls,
        message_type=message_type,
        profile_name=profile_name,
        wa_id=wa_id,
    )


def ensure_not_duplicate_event(db: Session, message_sid: str) -> bool:
    event_id = f"message_{message_sid}"

    try:
        processed_webhook_service.get_processed_webhook_by_event_id(db, event_id)
        return False
    except exceptions.NotFoundException:
        processed_webhook_service.create_processed_webhook(
            db,
            ProcessedWebhookSchema(source="twilio", event_id=event_id),
        )
        return True


def get_or_create_customer(db: Session, payload: IncomingWhatsAppPayload):
    try:
        return customer_service.get_customer_by_whatsapp_number(
            db, payload.sender_number
        )
    except exceptions.NotFoundException:
        name = payload.profile_name
        display_name = payload.profile_name or name

        return customer_service.create_customer(
            db,
            CustomerSchema(
                name=name,
                whatsapp_number=payload.sender_number,
                display_name=display_name,
                extra_metadata={"wa_id": payload.wa_id} if payload.wa_id else None,
            ),
        )


def get_or_create_active_conversation(db: Session, customer_id: str):
    conversations = conversation_service.get_conversations_by_customer_id(
        db, customer_id
    )
    active_conversation = next(
        (c for c in conversations if c.status == utils.ConversationStatus.ACTIVE.value),
        None,
    )

    if active_conversation:
        return active_conversation

    return conversation_service.create_conversation(
        db,
        ConversationSchema(customer_id=customer_id),
    )


def log_customer_inbound_message(
    db: Session, conversation_id: str, payload: IncomingWhatsAppPayload
) -> None:
    message_service.create_message(
        db,
        MessageSchema(
            conversation_id=conversation_id,
            sender_type=utils.MessageSenderType.CUSTOMER.value,
            direction=utils.MessageDirection.INBOUND.value,
            message_type=payload.message_type,
            content=payload.body,
            media_urls=payload.media_urls or None,
            status=utils.MessageStatus.DELIVERED.value,
            whatsapp_message_id=payload.message_sid,
        ),
    )


# def log_customer_outbound_message(
#     db: Session, conversation_id: str, content: str, media_urls: list[str] | None = None
# ) -> None:
#     message_service.create_message(
#         db,
#         MessageSchema(
#             conversation_id=conversation_id,
#             sender_type=utils.MessageSenderType.AI.value,
#             direction=utils.MessageDirection.OUTBOUND.value,
#             message_type=utils.MessageType.TEXT.value,
#             content=content,
#             media_urls=media_urls,
#             status=utils.MessageStatus.SENT.value,
#         ),
#     )

def _resolve_message_type(form: Mapping[str, Any], num_media: int) -> str:
    if not num_media:
        return utils.MessageType.TEXT.value

    def _map_content_type(content_type: str) -> str:
        if content_type.startswith("image/"):
            return utils.MessageType.IMAGE.value
        if content_type.startswith("video/"):
            return utils.MessageType.VIDEO.value
        if content_type.startswith("audio/"):
            return utils.MessageType.AUDIO.value
        return utils.MessageType.DOCUMENT.value

    resolved_types = {
        _map_content_type((form.get(f"MediaContentType{i}", "") or "").strip().lower())
        for i in range(num_media)
    }

    if len(resolved_types) == 1:
        return next(iter(resolved_types))

    return utils.MessageType.DOCUMENT.value
