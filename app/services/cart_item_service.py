from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import cart_item_schema
from ..core import exceptions
from ..db.model import cart_item_model


async def create_cart_item(db: AsyncSession, cart_item_data: cart_item_schema.CartItemSchema) -> cart_item_schema.CartItemResponse:
    new_cart_item = cart_item_model.CartItem(
        cart_id=cart_item_data.cart_id,
        product_id=cart_item_data.product_id,
        variant_id=cart_item_data.variant_id,
        quantity=cart_item_data.quantity,
        unit_price=cart_item_data.unit_price,
        subtotal=cart_item_data.subtotal
    )

    db.add(new_cart_item)
    await db.commit()
    await db.refresh(new_cart_item)

    return cart_item_schema.CartItemResponse.model_validate(new_cart_item)


async def get_cart_item_by_id(db: AsyncSession, cart_item_id: str) -> cart_item_schema.CartItemResponse:
    result = await db.execute(
        select(cart_item_model.CartItem).filter(cart_item_model.CartItem.id == cart_item_id)
    )
    cart_item = result.scalars().first()

    if not cart_item:
        raise exceptions.NotFoundException("Cart item not found.")

    return cart_item_schema.CartItemResponse.model_validate(cart_item)


async def get_all_cart_items(db: AsyncSession) -> list[cart_item_schema.CartItemResponse]:
    result = await db.execute(select(cart_item_model.CartItem))
    items = result.scalars().all()
    return [cart_item_schema.CartItemResponse.model_validate(i) for i in items]


async def get_cart_items_by_cart_id(db: AsyncSession, cart_id: str) -> list[cart_item_schema.CartItemResponse]:
    result = await db.execute(
        select(cart_item_model.CartItem).filter(cart_item_model.CartItem.cart_id == cart_id)
    )
    items = result.scalars().all()
    return [cart_item_schema.CartItemResponse.model_validate(i) for i in items]


async def update_cart_item(db: AsyncSession, cart_item_id: str, cart_item_data: cart_item_schema.CartItemSchema) -> cart_item_schema.CartItemResponse:
    result = await db.execute(
        select(cart_item_model.CartItem).filter(cart_item_model.CartItem.id == cart_item_id)
    )
    cart_item = result.scalars().first()

    if not cart_item:
        raise exceptions.NotFoundException("Cart item not found.")

    cart_item.cart_id = cart_item_data.cart_id
    cart_item.product_id = cart_item_data.product_id
    cart_item.variant_id = cart_item_data.variant_id
    cart_item.quantity = cart_item_data.quantity
    cart_item.unit_price = cart_item_data.unit_price
    cart_item.subtotal = cart_item_data.subtotal

    await db.commit()
    await db.refresh(cart_item)

    return cart_item_schema.CartItemResponse.model_validate(cart_item)


async def delete_cart_item(db: AsyncSession, cart_item_id: str):
    result = await db.execute(
        select(cart_item_model.CartItem).filter(cart_item_model.CartItem.id == cart_item_id)
    )
    cart_item = result.scalars().first()

    if not cart_item:
        raise exceptions.NotFoundException("Cart item not found.")

    await db.delete(cart_item)
    await db.commit()
