"""Orchestrates order status changes with history logging, WhatsApp notifications, and WebSocket broadcasts."""

from datetime import datetime, timezone
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import exceptions, utils
from ..db.model.order_model import Order
from ..db.model.order_item_model import OrderItem
from ..db.model.order_status_history_model import OrderStatusHistory
from ..db.schemas import order_schema, order_item_schema, order_status_history_schema
from . import whatsapp_service, websocket_service


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


VALID_TRANSITIONS = {
    "pending": {
        "paid",
        "shipped",
        "cancelled",
    },  # shipped without payment = pay on delivery
    "paid": {"shipped", "cancelled"},
    "shipped": {"delivered", "paid"},  # paid after delivery (POD confirmation)
    "delivered": {"paid"},  # late payment confirmation
    "cancelled": set(),
}

STATUS_EMOJI = {
    "pending": "🕐",
    "paid": "💰",
    "shipped": "🚚",
    "delivered": "✅",
    "cancelled": "❌",
}


# ── Status History ──────────────────────────────────────────────


async def create_history_entry(
    db: AsyncSession,
    order_id: str,
    old_status: str | None,
    new_status: str,
    changed_by_type: str = "system",
    changed_by_id: str | None = None,
    changed_by_name: str | None = None,
    notes: str | None = None,
) -> OrderStatusHistory:
    """Record a status change in the history table."""
    entry = OrderStatusHistory(
        order_id=order_id,
        old_status=old_status,
        new_status=new_status,
        changed_by_type=changed_by_type,
        changed_by_id=changed_by_id,
        changed_by_name=changed_by_name,
        notes=notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_order_timeline(
    db: AsyncSession, order_id: str
) -> list[order_status_history_schema.OrderStatusHistoryResponse]:
    """Get chronological status history for an order."""
    result = await db.execute(
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.created_at.asc())
    )
    return [
        order_status_history_schema.OrderStatusHistoryResponse.model_validate(r)
        for r in result.scalars().all()
    ]


# ── Status Update with Tracking ─────────────────────────────────


async def update_status_with_tracking(
    db: AsyncSession,
    order_id: str,
    body: order_schema.UpdateOrderStatusWithDetails,
    changed_by_type: str = "staff",
    changed_by_id: str | None = None,
    changed_by_name: str | None = None,
) -> order_schema.OrderResponse:
    """Update order status with history logging, notification, and broadcast."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise exceptions.NotFoundException("Order not found.")

    old_status = order.status
    new_status = body.status.value

    # Validate transition
    allowed = VALID_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise exceptions.BadRequestException(
            f"Cannot transition from '{old_status}' to '{new_status}'. "
            f"Allowed: {', '.join(allowed) if allowed else 'none (terminal status)'}."
        )

    # Update order
    order.status = new_status

    if new_status == utils.OrderStatus.SHIPPED.value:
        order.shipped_at = _utc_now()
        if body.estimated_delivery_date:
            order.estimated_delivery_date = body.estimated_delivery_date

    elif new_status == utils.OrderStatus.DELIVERED.value:
        order.delivered_at = _utc_now()

    await db.commit()
    await db.refresh(order)

    # Record history
    await create_history_entry(
        db,
        str(order.id),
        old_status,
        new_status,
        changed_by_type,
        changed_by_id,
        changed_by_name,
        body.notes,
    )

    # Notify customer via WhatsApp
    if body.notify_customer and order.customer_whatsapp_number:
        try:
            await _send_status_notification(order, old_status, new_status, body.notes)
        except Exception:
            logger.opt(exception=True).warning(
                "order_tracking: failed to notify customer for order={}",
                order.order_number,
            )

    # Broadcast to dashboard
    try:
        await websocket_service.broadcast(
            utils.WebSocketEvent.ORDER_STATUS_CHANGED.value,
            {
                "order_id": str(order.id),
                "order_number": order.order_number,
                "old_status": old_status,
                "new_status": new_status,
                "changed_by": changed_by_name or changed_by_type,
            },
        )
    except Exception:
        pass

    return order_schema.OrderResponse.model_validate(order)


# ── Per-Item Delivery Status ─────────────────────────────────────


async def update_item_delivery_status(
    db: AsyncSession,
    order_id: str,
    item_id: str,
    body: order_schema.UpdateItemDeliveryStatus,
    changed_by_type: str = "staff",
    changed_by_id: str | None = None,
    changed_by_name: str | None = None,
) -> order_item_schema.OrderItemResponse:
    """Update delivery status for a single order item. Auto-promotes order status if all items match."""
    result = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    item = result.scalars().first()
    if not item:
        raise exceptions.NotFoundException("Order item not found.")

    old_item_status = item.delivery_status
    item.delivery_status = body.delivery_status.value
    await db.commit()
    await db.refresh(item)

    # Log history
    await create_history_entry(
        db,
        order_id,
        old_item_status,
        body.delivery_status.value,
        changed_by_type,
        changed_by_id,
        changed_by_name,
        notes=body.notes
        or f"Item '{item.product_name}' marked as {body.delivery_status.value}",
    )

    # Auto-promote order status based on item statuses
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalars().first()
    if order and order.order_items:
        all_statuses = [i.delivery_status for i in order.order_items]

        if all(s == utils.DeliveryStatus.DELIVERED.value for s in all_statuses):
            if order.status != utils.OrderStatus.DELIVERED.value:
                old = order.status
                order.status = utils.OrderStatus.DELIVERED.value
                order.delivered_at = _utc_now()
                await db.commit()
                await create_history_entry(
                    db,
                    order_id,
                    old,
                    utils.OrderStatus.DELIVERED.value,
                    "system",
                    notes="All items delivered — order auto-promoted",
                )
        elif any(s == utils.DeliveryStatus.SHIPPED.value for s in all_statuses):
            if order.status == utils.OrderStatus.PAID.value:
                old = order.status
                order.status = utils.OrderStatus.SHIPPED.value
                order.shipped_at = _utc_now()
                await db.commit()
                await create_history_entry(
                    db,
                    order_id,
                    old,
                    utils.OrderStatus.SHIPPED.value,
                    "system",
                    notes="Partial shipment — order auto-promoted to shipped",
                )

    # Notify customer
    if body.notify_customer and order and order.customer_whatsapp_number:
        try:
            remaining = sum(
                1
                for i in order.order_items
                if i.delivery_status != body.delivery_status.value
            )
            msg = (
                f"Update on order *{order.order_number}*\n\n"
                f"*{item.product_name}* has been marked as *{body.delivery_status.value}*."
            )
            if remaining > 0:
                msg += f"\n({remaining} item(s) still being processed)"
            await whatsapp_service.send_message(
                to=order.customer_whatsapp_number, body=msg
            )
        except Exception:
            logger.opt(exception=True).warning(
                "order_tracking: failed to notify for item update"
            )

    return order_item_schema.OrderItemResponse.model_validate(item)


# ── WhatsApp Notification Templates ──────────────────────────────


async def _send_status_notification(
    order: Order, old_status: str, new_status: str, notes: str | None = None
):
    """Send a WhatsApp notification to the customer about their order status change."""
    phone = order.customer_whatsapp_number
    if not phone:
        return

    if new_status == utils.OrderStatus.PAID.value:
        body = (
            f"💰 Payment confirmed for order *{order.order_number}*!\n\n"
            f"Your order is now being processed. We'll notify you when it ships.\n\n"
            f"Total: *NGN {order.total_amount:,.2f}*"
        )
        await whatsapp_service.send_message(to=phone, body=body)

    elif new_status == utils.OrderStatus.SHIPPED.value:
        body = f"🚚 Your order *{order.order_number}* has been shipped!\n"
        body += f"\n🔍 Tracking ID: *{order.order_number}*"
        if order.estimated_delivery_date:
            body += f"\n📅 Est. Delivery: *{order.estimated_delivery_date.strftime('%a %d %b %Y')}*"
        if order.address_line:
            body += f"\n📍 Delivery to: {order.address_line}, {order.address_city}"
        body += "\n\nWe'll notify you when it arrives!"

        try:
            await whatsapp_service.send_interactive_buttons(
                to=phone,
                body=body,
                buttons=[{"id": f"track|{order.order_number}", "title": "Track Order"}],
            )
        except Exception:
            await whatsapp_service.send_message(to=phone, body=body)

    elif new_status == utils.OrderStatus.DELIVERED.value:
        body = (
            f"🎉 Order *{order.order_number}* has been delivered!\n\n"
            f"We hope you love your purchase. Thank you for shopping with us!\n\n"
            f"If you have any issues, just message us."
        )
        await whatsapp_service.send_message(to=phone, body=body)

    elif new_status == utils.OrderStatus.CANCELLED.value:
        body = f"❌ Order *{order.order_number}* has been cancelled."
        if notes:
            body += f"\nReason: {notes}"
        body += "\n\nIf you have questions, please reach out to us."
        await whatsapp_service.send_message(to=phone, body=body)
