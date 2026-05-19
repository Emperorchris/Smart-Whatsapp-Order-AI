from fastapi import APIRouter, Request, Response
from ...core.dependencies import DBSession
from ...core import utils, exceptions
from ...services import processed_webhook_service, message_service
from ...db.schemas import processed_webhook_schema
from ...db.schemas.processed_webhook_schema import ProcessedWebhookSchema

webhook_router = APIRouter(prefix="/webhooks/processed", tags=["Processed Webhooks"])


@webhook_router.post("/", response_model=processed_webhook_schema.ProcessedWebhookResponse)
def create_processed_webhook(webhook_data: processed_webhook_schema.ProcessedWebhookSchema, db: DBSession):
    return processed_webhook_service.create_processed_webhook(db, webhook_data)


@webhook_router.get("/", response_model=list[processed_webhook_schema.ProcessedWebhookResponse])
def get_all_processed_webhooks(db: DBSession):
    return processed_webhook_service.get_all_processed_webhooks(db)


@webhook_router.get("/{webhook_id}", response_model=processed_webhook_schema.ProcessedWebhookResponse)
def get_processed_webhook(webhook_id: str, db: DBSession):
    return processed_webhook_service.get_processed_webhook_by_id(db, webhook_id)


@webhook_router.get("/event/{event_id}", response_model=processed_webhook_schema.ProcessedWebhookResponse)
def get_processed_webhook_by_event(event_id: str, db: DBSession):
    return processed_webhook_service.get_processed_webhook_by_event_id(db, event_id)


@webhook_router.delete("/{webhook_id}", status_code=204)
def delete_processed_webhook(webhook_id: str, db: DBSession):
    processed_webhook_service.delete_processed_webhook(db, webhook_id)


@webhook_router.post("/twilio/status")
async def twilio_status_callback(db: DBSession, request: Request):
    form = await request.form()

    message_sid = form.get("MessageSid", "")
    message_status = form.get("MessageStatus", "")

    if not message_sid or not message_status:
        return Response(content="", media_type="text/xml")

    # Prevent duplicate processing
    event_id = f"status_{message_sid}_{message_status}"
    try:
        processed_webhook_service.get_processed_webhook_by_event_id(db, event_id)
        return Response(content="", media_type="text/xml")
    except exceptions.NotFoundException:
        pass

    processed_webhook_service.create_processed_webhook(
        db, ProcessedWebhookSchema(source="twilio", event_id=event_id)
    )

    # Map Twilio status to our MessageStatus enum
    status_map = {
        "delivered": utils.MessageStatus.DELIVERED.value,
        "read": utils.MessageStatus.READ.value,
        "failed": utils.MessageStatus.FAILED.value,
        "undelivered": utils.MessageStatus.UNDELIVERED.value,
    }

    mapped_status = status_map.get(message_status.lower())
    if not mapped_status:
        return Response(content="", media_type="text/xml")

    # Find and update the message
    try:
        message = message_service.get_message_by_whatsapp_message_id(db, message_sid)
        message_service.update_message_status(db, str(message.id), mapped_status)
    except exceptions.NotFoundException:
        pass

    return Response(content="", media_type="text/xml")
