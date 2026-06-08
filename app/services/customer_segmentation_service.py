"""
Auto-segments customers based on order behavior:
- new: 0 orders
- returning: 1-4 orders
- vip: 5+ orders OR total_spent >= threshold
- churned: last order > 90 days ago
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import utils
from ..db.model.customer_model import Customer
from ..db.model.order_model import Order


VIP_MIN_ORDERS = 5
VIP_MIN_SPENT = Decimal("100000")  # NGN 100k
CHURN_DAYS = 90


async def auto_segment_customers(db: AsyncSession) -> dict:
    """Re-classify all customers into segments (new, returning, vip, churned) based on order history."""
    now = datetime.now(tz=timezone.utc).replace(tzinfo=None)

    # Aggregate per customer
    query = (
        select(
            Customer.id,
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_spent"),
            func.max(Order.created_at).label("last_order_at"),
        )
        .outerjoin(Order, (Order.customer_id == Customer.id) & (Order.status != utils.OrderStatus.CANCELLED.value))
        .group_by(Customer.id)
    )

    rows = (await db.execute(query)).all()

    counts = {"new": 0, "returning": 0, "vip": 0, "churned": 0}

    for r in rows:
        if r.order_count == 0:
            segment = utils.CustomerSegment.NEW.value
        elif r.last_order_at and (now - r.last_order_at).days > CHURN_DAYS:
            segment = utils.CustomerSegment.CHURNED.value
        elif r.order_count >= VIP_MIN_ORDERS or r.total_spent >= VIP_MIN_SPENT:
            segment = utils.CustomerSegment.VIP.value
        else:
            segment = utils.CustomerSegment.RETURNING.value

        # Update in-place
        await db.execute(
            Customer.__table__.update()
            .where(Customer.id == r.id)
            .values(customer_segment=segment)
        )
        counts[segment] += 1

    await db.commit()
    return counts


async def get_segment_summary(db: AsyncSession) -> list[dict]:
    """Return customer counts grouped by segment."""
    query = (
        select(
            Customer.customer_segment.label("segment"),
            func.count(Customer.id).label("count"),
        )
        .group_by(Customer.customer_segment)
        .order_by(func.count(Customer.id).desc())
    )
    rows = (await db.execute(query)).all()
    return [{"segment": r.segment, "count": r.count} for r in rows]


async def get_customers_by_segment(
    db: AsyncSession,
    segment: str,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Return a paginated list of customers belonging to the specified segment."""
    base = select(Customer).where(Customer.customer_segment == segment)
    count_q = select(func.count(Customer.id)).where(Customer.customer_segment == segment)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Customer.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    return {
        "segment": segment,
        "total": total,
        "page": page,
        "page_size": page_size,
        "customers": [
            {
                "id": str(c.id),
                "name": c.name,
                "whatsapp_number": c.whatsapp_number,
                "segment": c.customer_segment,
                "created_at": c.created_at.isoformat(),
            }
            for c in rows
        ],
    }
