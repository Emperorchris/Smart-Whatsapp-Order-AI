from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import order_schema
from ..core import exceptions, utils
from ..db.model import order_model


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
        delivery_address=order_data.delivery_address,
        extra_metadata=order_data.extra_metadata
    )

    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    return order_schema.OrderResponse.model_validate(new_order)


async def get_order_by_id(db: AsyncSession, order_id: str) -> order_schema.OrderResponse:
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.id == order_id)
    )
    order = result.scalars().first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    return order_schema.OrderResponse.model_validate(order)


async def get_all_orders(db: AsyncSession) -> list[order_schema.OrderResponse]:
    result = await db.execute(select(order_model.Order))
    orders = result.scalars().all()
    return [order_schema.OrderResponse.model_validate(o) for o in orders]


async def get_order_by_order_number(db: AsyncSession, order_number: str) -> order_schema.OrderResponse:
    result = await db.execute(
        select(order_model.Order).filter(order_model.Order.order_number == order_number)
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
    order.delivery_address = order_data.delivery_address
    order.extra_metadata = order_data.extra_metadata

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
