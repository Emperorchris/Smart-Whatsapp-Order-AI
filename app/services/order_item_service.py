from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import order_item_schema
from ..core import exceptions
from ..db.model import order_item_model


async def create_order_item(db: AsyncSession, order_item_data: order_item_schema.OrderItemSchema) -> order_item_schema.OrderItemResponse:
    new_order_item = order_item_model.OrderItem(
        order_id=order_item_data.order_id,
        product_id=order_item_data.product_id,
        variant_id=order_item_data.variant_id,
        product_name=order_item_data.product_name,
        product_sku=order_item_data.product_sku,
        product_description=order_item_data.product_description,
        product_category=order_item_data.product_category,
        product_media=order_item_data.product_media,
        product_variant_attributes=order_item_data.product_variant_attributes,
        quantity=order_item_data.quantity,
        unit_price=order_item_data.unit_price,
        subtotal=order_item_data.subtotal,
        delivery_status=order_item_data.delivery_status,
    )

    db.add(new_order_item)
    await db.commit()
    await db.refresh(new_order_item)

    return order_item_schema.OrderItemResponse.model_validate(new_order_item)


async def get_order_item_by_id(db: AsyncSession, order_item_id: str) -> order_item_schema.OrderItemResponse:
    result = await db.execute(
        select(order_item_model.OrderItem).filter(order_item_model.OrderItem.id == order_item_id)
    )
    order_item = result.scalars().first()

    if not order_item:
        raise exceptions.NotFoundException("Order item not found.")

    return order_item_schema.OrderItemResponse.model_validate(order_item)


async def get_all_order_items(db: AsyncSession) -> list[order_item_schema.OrderItemResponse]:
    result = await db.execute(select(order_item_model.OrderItem))
    items = result.scalars().all()
    return [order_item_schema.OrderItemResponse.model_validate(i) for i in items]


async def get_order_items_by_order_id(db: AsyncSession, order_id: str) -> list[order_item_schema.OrderItemResponse]:
    result = await db.execute(
        select(order_item_model.OrderItem).filter(order_item_model.OrderItem.order_id == order_id)
    )
    items = result.scalars().all()
    return [order_item_schema.OrderItemResponse.model_validate(i) for i in items]


async def update_order_item(db: AsyncSession, order_item_id: str, order_item_data: order_item_schema.OrderItemSchema) -> order_item_schema.OrderItemResponse:
    result = await db.execute(
        select(order_item_model.OrderItem).filter(order_item_model.OrderItem.id == order_item_id)
    )
    order_item = result.scalars().first()

    if not order_item:
        raise exceptions.NotFoundException("Order item not found.")

    order_item.order_id = order_item_data.order_id
    order_item.product_id = order_item_data.product_id
    order_item.variant_id = order_item_data.variant_id
    order_item.product_name = order_item_data.product_name
    order_item.product_sku = order_item_data.product_sku
    order_item.product_description = order_item_data.product_description
    order_item.product_category = order_item_data.product_category
    order_item.product_media = order_item_data.product_media
    order_item.product_variant_attributes = order_item_data.product_variant_attributes
    order_item.quantity = order_item_data.quantity
    order_item.unit_price = order_item_data.unit_price
    order_item.subtotal = order_item_data.subtotal
    order_item.delivery_status = order_item_data.delivery_status

    await db.commit()
    await db.refresh(order_item)

    return order_item_schema.OrderItemResponse.model_validate(order_item)


async def delete_order_item(db: AsyncSession, order_item_id: str):
    result = await db.execute(
        select(order_item_model.OrderItem).filter(order_item_model.OrderItem.id == order_item_id)
    )
    order_item = result.scalars().first()

    if not order_item:
        raise exceptions.NotFoundException("Order item not found.")

    await db.delete(order_item)
    await db.commit()
