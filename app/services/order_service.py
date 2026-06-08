from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import customer_address_schema

from ..db.schemas import order_schema
from ..core import exceptions, utils
from ..db.model import order_model
from . import websocket_service


async def create_order(db: AsyncSession, order_data: order_schema.OrderSchema) -> order_schema.OrderResponse:
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.order_number == order_data.order_number)
    )
    if result.scalars().first():
        raise exceptions.ConflictException("An order with this order number already exists.")

    new_order = order_model.Order(
        customer_id=order_data.customer_id,
        order_number=order_data.order_number,
        customer_name=order_data.customer_name,
        customer_whatsapp_number=order_data.customer_whatsapp_number,
        status=order_data.status,
        total_amount=order_data.total_amount,
        payment_status=order_data.payment_status,
        address_label=order_data.address_label,
        address_full_name=order_data.address_full_name,
        address_phone_number=order_data.address_phone_number,
        address_line=order_data.address_line,
        address_city=order_data.address_city,
        address_state=order_data.address_state,
        address_country=order_data.address_country,
        address_postal_code=order_data.address_postal_code,
        address_landmark=order_data.address_landmark,
        extra_metadata=order_data.extra_metadata,
    )

    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    response = order_schema.OrderResponse.model_validate(new_order)

    # Broadcast new order to dashboard
    try:
        await websocket_service.broadcast(
            utils.WebSocketEvent.NEW_ORDER.value,
            {
                "order_id": str(response.id),
                "order_number": response.order_number,
                "customer_id": str(response.customer_id) if response.customer_id else None,
                "customer_name": response.customer_name,
                "status": response.status,
                "payment_status": response.payment_status,
                "total_amount": str(response.total_amount),
                "created_at": response.created_at.isoformat() if response.created_at else None,
            },
        )
    except Exception:
        pass

    return response


async def get_order_by_id(db: AsyncSession, order_id: str) -> order_schema.OrderResponse:
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.id == order_id)
    )
    order = result.scalars().first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    return order_schema.OrderResponse.model_validate(order)


async def get_all_orders(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[order_schema.OrderResponse]:
    result = await db.execute(
        select(order_model.Order).order_by(order_model.Order.created_at.desc()).offset(skip).limit(limit)
    )
    orders = result.scalars().all()
    return [order_schema.OrderResponse.model_validate(o) for o in orders]


async def get_order_by_order_number(db: AsyncSession, order_number: str) -> order_schema.OrderResponse:
    # Try exact match first
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.order_number == order_number)
    )
    order = result.scalars().first()

    # Fallback: try matching just the numeric part using ilike
    if not order:
        # Extract digits from the input (e.g. "ORD-123" or "#ORD-123" or "123" → "123")
        digits = ''.join(c for c in order_number if c.isdigit())
        if digits:
            result = await db.execute(
                select(order_model.Order).filter(
                    order_model.Order.order_number.ilike(f"%{digits}")
                )
            )
            order = result.scalars().first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    return order_schema.OrderResponse.model_validate(order)


async def get_orders_by_customer_id(db: AsyncSession, customer_id: str) -> list[order_schema.OrderResponse]:
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.customer_id == customer_id)
    )
    orders = result.scalars().all()
    return [order_schema.OrderResponse.model_validate(o) for o in orders]


async def update_order(db: AsyncSession, order_id: str, order_data: order_schema.OrderSchema) -> order_schema.OrderResponse:
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.id == order_id)
    )
    order = result.scalars().first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    dup_result = await db.execute(
        select(order_model.Order).filter(
            order_model.Order.order_number == order_data.order_number,
            order_model.Order.id != order_id
        )
    )
    if dup_result.scalars().first():
        raise exceptions.ConflictException("Order number is already taken by another order.")

    order.customer_id = order_data.customer_id
    order.order_number = order_data.order_number
    order.customer_name = order_data.customer_name
    order.customer_whatsapp_number = order_data.customer_whatsapp_number
    order.status = order_data.status
    order.total_amount = order_data.total_amount
    order.payment_status = order_data.payment_status
    order.address_label = order_data.address_label
    order.address_full_name = order_data.address_full_name
    order.address_phone_number = order_data.address_phone_number
    order.address_line = order_data.address_line
    order.address_city = order_data.address_city
    order.address_state = order_data.address_state
    order.address_country = order_data.address_country
    order.address_postal_code = order_data.address_postal_code
    order.address_landmark = order_data.address_landmark
    order.extra_metadata = order_data.extra_metadata

    await db.commit()
    await db.refresh(order)

    return order_schema.OrderResponse.model_validate(order)



async def update_order_status(db: AsyncSession, order_id: str, new_status: str) -> order_schema.OrderResponse:
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.id == order_id)
    )
    order = result.scalars().first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    if new_status not in utils.OrderStatus._value2member_map_:
        raise exceptions.BadRequestException("Invalid order status.")

    order.status = new_status
    await db.commit()
    await db.refresh(order)

    return order_schema.OrderResponse.model_validate(order)


async def update_order_address(db: AsyncSession, order_id: str, address_data: customer_address_schema.CustomerAddressSchema) -> order_schema.OrderResponse:
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.id == order_id)
    )
    order = result.scalars().first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    order.address_label = address_data.label
    order.address_full_name = address_data.full_name
    order.address_phone_number = address_data.phone_number
    order.address_line = address_data.address_line
    order.address_city = address_data.city
    order.address_state = address_data.state
    order.address_country = address_data.country
    order.address_postal_code = address_data.postal_code
    order.address_landmark = address_data.landmark

    await db.commit()
    await db.refresh(order)

    return order_schema.OrderResponse.model_validate(order)


async def cancel_order(db: AsyncSession, order_id: str) -> order_schema.OrderResponse:
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.id == order_id)
    )
    order = result.scalars().first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    if order.status in [utils.OrderStatus.CANCELLED.value, utils.OrderStatus.DELIVERED.value]:
        raise exceptions.BadRequestException(f"Cannot cancel an order that is already {order.status}.")

    order.status = utils.OrderStatus.CANCELLED.value
    await db.commit()
    await db.refresh(order)

    return order_schema.OrderResponse.model_validate(order)


async def delete_order(db: AsyncSession, order_id: str):
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.id == order_id)
    )
    order = result.scalars().first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    await db.delete(order)
    await db.commit()


TERMINAL_STATUSES = {utils.OrderStatus.CANCELLED.value, utils.OrderStatus.DELIVERED.value}


async def bulk_update_order_status(
    db: AsyncSession,
    order_ids: list,
    new_status: utils.OrderStatus,
) -> order_schema.BulkOrderStatusResponse:
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.id.in_(order_ids))
    )
    orders = list(result.scalars().all())

    found_ids = {o.id for o in orders}
    failed_ids = [oid for oid in order_ids if oid not in found_ids]

    updated = []
    for order in orders:
        if order.status in TERMINAL_STATUSES:
            failed_ids.append(order.id)
            continue
        order.status = new_status.value
        updated.append(order)

    await db.commit()
    for o in updated:
        await db.refresh(o)

    return order_schema.BulkOrderStatusResponse(
        updated_count=len(updated),
        failed_ids=failed_ids,
        updated_orders=[order_schema.OrderResponse.model_validate(o) for o in updated],
    )
