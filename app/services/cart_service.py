from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import cart_schema
from ..core import exceptions
from ..db.model import carts_model


async def create_cart(db: AsyncSession, cart_data: cart_schema.CartSchema) -> cart_schema.CartResponse:
    new_cart = carts_model.Cart(
        customer_id=cart_data.customer_id,
        status=cart_data.status
    )

    db.add(new_cart)
    await db.commit()
    await db.refresh(new_cart)

    return cart_schema.CartResponse.model_validate(new_cart)


async def get_cart_by_id(db: AsyncSession, cart_id: str) -> cart_schema.CartResponse:
    result = await db.execute(
        select(carts_model.Cart).filter(carts_model.Cart.id == cart_id)
    )
    cart = result.scalars().first()

    if not cart:
        raise exceptions.NotFoundException("Cart not found.")

    return cart_schema.CartResponse.model_validate(cart)


async def get_all_carts(db: AsyncSession) -> list[cart_schema.CartResponse]:
    result = await db.execute(select(carts_model.Cart))
    carts = result.scalars().all()
    return [cart_schema.CartResponse.model_validate(c) for c in carts]


async def get_cart_by_customer_id(db: AsyncSession, customer_id: str) -> cart_schema.CartResponse:
    result = await db.execute(
        select(carts_model.Cart).filter(
            carts_model.Cart.customer_id == customer_id,
            carts_model.Cart.status == "active"
        )
    )
    cart = result.scalars().first()

    if not cart:
        raise exceptions.NotFoundException("Active cart not found for this customer.")

    return cart_schema.CartResponse.model_validate(cart)


async def get_carts_by_customer_id(db: AsyncSession, customer_id: str) -> list[cart_schema.CartResponse]:
    result = await db.execute(
        select(carts_model.Cart).filter(
            carts_model.Cart.customer_id == customer_id,
        )
    )
    carts = result.scalars().all()
    return [cart_schema.CartResponse.model_validate(c) for c in carts]


async def update_cart(db: AsyncSession, cart_id: str, cart_data: cart_schema.CartSchema) -> cart_schema.CartResponse:
    result = await db.execute(
        select(carts_model.Cart).filter(carts_model.Cart.id == cart_id)
    )
    cart = result.scalars().first()

    if not cart:
        raise exceptions.NotFoundException("Cart not found.")

    cart.customer_id = cart_data.customer_id
    cart.status = cart_data.status

    await db.commit()
    await db.refresh(cart)

    return cart_schema.CartResponse.model_validate(cart)


async def delete_cart(db: AsyncSession, cart_id: str):
    result = await db.execute(
        select(carts_model.Cart).filter(carts_model.Cart.id == cart_id)
    )
    cart = result.scalars().first()

    if not cart:
        raise exceptions.NotFoundException("Cart not found.")

    await db.delete(cart)
    await db.commit()
