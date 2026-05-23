from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import processed_webhook_schema
from ..core import exceptions
from ..db.model import processed_webhook_model


async def create_processed_webhook(db: AsyncSession, webhook_data: processed_webhook_schema.ProcessedWebhookSchema) -> processed_webhook_schema.ProcessedWebhookResponse:
    result = await db.execute(
        select(processed_webhook_model.ProcessedWebhook).filter(
            processed_webhook_model.ProcessedWebhook.event_id == webhook_data.event_id
        )
    )
    if result.scalars().first():
        raise exceptions.ConflictException("This webhook event has already been processed.")

    new_webhook = processed_webhook_model.ProcessedWebhook(
        source=webhook_data.source,
        event_id=webhook_data.event_id
    )

    db.add(new_webhook)
    await db.commit()
    await db.refresh(new_webhook)

    return processed_webhook_schema.ProcessedWebhookResponse.model_validate(new_webhook)


async def get_processed_webhook_by_id(db: AsyncSession, webhook_id: str) -> processed_webhook_schema.ProcessedWebhookResponse:
    result = await db.execute(
        select(processed_webhook_model.ProcessedWebhook).filter(
            processed_webhook_model.ProcessedWebhook.id == webhook_id
        )
    )
    webhook = result.scalars().first()

    if not webhook:
        raise exceptions.NotFoundException("Processed webhook not found.")

    return processed_webhook_schema.ProcessedWebhookResponse.model_validate(webhook)


async def get_all_processed_webhooks(db: AsyncSession) -> list[processed_webhook_schema.ProcessedWebhookResponse]:
    result = await db.execute(select(processed_webhook_model.ProcessedWebhook))
    webhooks = result.scalars().all()
    return [processed_webhook_schema.ProcessedWebhookResponse.model_validate(w) for w in webhooks]


async def get_processed_webhook_by_event_id(db: AsyncSession, event_id: str) -> processed_webhook_schema.ProcessedWebhookResponse:
    result = await db.execute(
        select(processed_webhook_model.ProcessedWebhook).filter(
            processed_webhook_model.ProcessedWebhook.event_id == event_id
        )
    )
    webhook = result.scalars().first()

    if not webhook:
        raise exceptions.NotFoundException("Processed webhook not found.")

    return processed_webhook_schema.ProcessedWebhookResponse.model_validate(webhook)


async def delete_processed_webhook(db: AsyncSession, webhook_id: str):
    result = await db.execute(
        select(processed_webhook_model.ProcessedWebhook).filter(
            processed_webhook_model.ProcessedWebhook.id == webhook_id
        )
    )
    webhook = result.scalars().first()

    if not webhook:
        raise exceptions.NotFoundException("Processed webhook not found.")

    await db.delete(webhook)
    await db.commit()
