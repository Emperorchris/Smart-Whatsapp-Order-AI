from ..db.schemas import processed_webhook_schema
from ..core import exceptions
from ..db.model import processed_webhook_model
from sqlalchemy.orm import Session


def create_processed_webhook(db: Session, webhook_data: processed_webhook_schema.ProcessedWebhookSchema) -> processed_webhook_schema.ProcessedWebhookResponse:
    existing = db.query(processed_webhook_model.ProcessedWebhook).filter(
        processed_webhook_model.ProcessedWebhook.event_id == webhook_data.event_id
    ).first()
    if existing:
        raise exceptions.ConflictException("This webhook event has already been processed.")

    new_webhook = processed_webhook_model.ProcessedWebhook(
        source=webhook_data.source,
        event_id=webhook_data.event_id
    )

    db.add(new_webhook)
    db.commit()
    db.refresh(new_webhook)

    return processed_webhook_schema.ProcessedWebhookResponse.model_validate(new_webhook)


def get_processed_webhook_by_id(db: Session, webhook_id: str) -> processed_webhook_schema.ProcessedWebhookResponse:
    webhook = db.query(processed_webhook_model.ProcessedWebhook).filter(
        processed_webhook_model.ProcessedWebhook.id == webhook_id).first()

    if not webhook:
        raise exceptions.NotFoundException("Processed webhook not found.")

    return processed_webhook_schema.ProcessedWebhookResponse.model_validate(webhook)


def get_all_processed_webhooks(db: Session) -> list[processed_webhook_schema.ProcessedWebhookResponse]:
    webhooks = db.query(processed_webhook_model.ProcessedWebhook).all()
    return [processed_webhook_schema.ProcessedWebhookResponse.model_validate(w) for w in webhooks]


def get_processed_webhook_by_event_id(db: Session, event_id: str) -> processed_webhook_schema.ProcessedWebhookResponse:
    webhook = db.query(processed_webhook_model.ProcessedWebhook).filter(
        processed_webhook_model.ProcessedWebhook.event_id == event_id).first()

    if not webhook:
        raise exceptions.NotFoundException("Processed webhook not found.")

    return processed_webhook_schema.ProcessedWebhookResponse.model_validate(webhook)


def delete_processed_webhook(db: Session, webhook_id: str):
    webhook = db.query(processed_webhook_model.ProcessedWebhook).filter(
        processed_webhook_model.ProcessedWebhook.id == webhook_id).first()

    if not webhook:
        raise exceptions.NotFoundException("Processed webhook not found.")

    db.delete(webhook)
    db.commit()
