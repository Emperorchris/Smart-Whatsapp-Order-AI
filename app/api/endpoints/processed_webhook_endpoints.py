from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import processed_webhook_service
from ...db.schemas import processed_webhook_schema

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
