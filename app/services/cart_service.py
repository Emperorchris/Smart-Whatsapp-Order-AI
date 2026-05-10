from ..db.schemas import cart_schema
from ..core import exceptions
from ..db.model import carts_model
from sqlalchemy.orm import Session


def create_cart(db: Session, cart_data: cart_schema.CartSchema) -> cart_schema.CartResponse:
    new_cart = carts_model.Cart(
        customer_id=cart_data.customer_id,
        status=cart_data.status
    )

    db.add(new_cart)
    db.commit()
    db.refresh(new_cart)

    return cart_schema.CartResponse.model_validate(new_cart)


def get_cart_by_id(db: Session, cart_id: str) -> cart_schema.CartResponse:
    cart = db.query(carts_model.Cart).filter(
        carts_model.Cart.id == cart_id).first()

    if not cart:
        raise exceptions.NotFoundException("Cart not found.")

    return cart_schema.CartResponse.model_validate(cart)


def get_all_carts(db: Session) -> list[cart_schema.CartResponse]:
    carts = db.query(carts_model.Cart).all()
    return [cart_schema.CartResponse.model_validate(c) for c in carts]


def get_carts_by_customer_id(db: Session, customer_id: str) -> list[cart_schema.CartResponse]:
    carts = db.query(carts_model.Cart).filter(
        carts_model.Cart.customer_id == customer_id).all()
    return [cart_schema.CartResponse.model_validate(c) for c in carts]


def update_cart(db: Session, cart_id: str, cart_data: cart_schema.CartSchema) -> cart_schema.CartResponse:
    cart = db.query(carts_model.Cart).filter(
        carts_model.Cart.id == cart_id).first()

    if not cart:
        raise exceptions.NotFoundException("Cart not found.")

    cart.customer_id = cart_data.customer_id
    cart.status = cart_data.status

    db.commit()
    db.refresh(cart)

    return cart_schema.CartResponse.model_validate(cart)


def delete_cart(db: Session, cart_id: str):
    cart = db.query(carts_model.Cart).filter(
        carts_model.Cart.id == cart_id).first()

    if not cart:
        raise exceptions.NotFoundException("Cart not found.")

    db.delete(cart)
    db.commit()
