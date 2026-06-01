import asyncio
from loguru import logger

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.model.customer_model import Customer
from . import whatsapp_service


async def broadcast_message(
    db: AsyncSession,
    message: str,
    segment: str | None = None,
    customer_ids: list[str] | None = None,
) -> dict:
    if customer_ids:
        query = select(Customer).where(Customer.id.in_(customer_ids))
    elif segment:
        query = select(Customer).where(Customer.customer_segment == segment)
    else:
        query = select(Customer)

    result = await db.execute(query)
    customers = list(result.scalars().all())

    sent = 0
    failed = 0
    failed_numbers = []

    for customer in customers:
        if not customer.whatsapp_number:
            failed += 1
            continue
        try:
            await whatsapp_service.send_message(to=customer.whatsapp_number, body=message)
            sent += 1
            # Rate limit: WhatsApp has per-second limits
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"broadcast: failed to send to {customer.whatsapp_number}: {e}")
            failed += 1
            failed_numbers.append(customer.whatsapp_number)

    return {
        "total_recipients": len(customers),
        "sent": sent,
        "failed": failed,
        "failed_numbers": failed_numbers,
    }
