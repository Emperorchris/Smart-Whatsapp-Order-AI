from ..db.schemas import cart_item_schema
from ..core import exceptions
from ..db.model import cart_item_model
from sqlalchemy.orm import Session


def create_cart_item(db: Session, cart_item_data: cart_item_schema.CartItemSchema) -> cart_item_schema.CartItemResponse:
    new_cart_item = cart_item_model.CartItem(
        cart_id=cart_item_data.cart_id,
        product_id=cart_item_data.product_id,
        quantity=cart_item_data.quantity,
        unit_price=cart_item_data.unit_price,
        subtotal=cart_item_data.subtotal
    )

    db.add(new_cart_item)
    db.commit()
    db.refresh(new_cart_item)

    return cart_item_schema.CartItemResponse.model_validate(new_cart_item)


def get_cart_item_by_id(db: Session, cart_item_id: str) -> cart_item_schema.CartItemResponse:
    cart_item = db.query(cart_item_model.CartItem).filter(
        cart_item_model.CartItem.id == cart_item_id).first()

    if not cart_item:
        raise exceptions.NotFoundException("Cart item not found.")

    return cart_item_schema.CartItemResponse.model_validate(cart_item)


def get_all_cart_items(db: Session) -> list[cart_item_schema.CartItemResponse]:
    items = db.query(cart_item_model.CartItem).all()
    return [cart_item_schema.CartItemResponse.model_validate(i) for i in items]


def get_cart_items_by_cart_id(db: Session, cart_id: str) -> list[cart_item_schema.CartItemResponse]:
    items = db.query(cart_item_model.CartItem).filter(
        cart_item_model.CartItem.cart_id == cart_id).all()
    return [cart_item_schema.CartItemResponse.model_validate(i) for i in items]


def update_cart_item(db: Session, cart_item_id: str, cart_item_data: cart_item_schema.CartItemSchema) -> cart_item_schema.CartItemResponse:
    cart_item = db.query(cart_item_model.CartItem).filter(
        cart_item_model.CartItem.id == cart_item_id).first()

    if not cart_item:
        raise exceptions.NotFoundException("Cart item not found.")

    cart_item.cart_id = cart_item_data.cart_id
    cart_item.product_id = cart_item_data.product_id
    cart_item.quantity = cart_item_data.quantity
    cart_item.unit_price = cart_item_data.unit_price
    cart_item.subtotal = cart_item_data.subtotal

    db.commit()
    db.refresh(cart_item)

    return cart_item_schema.CartItemResponse.model_validate(cart_item)


def delete_cart_item(db: Session, cart_item_id: str):
    cart_item = db.query(cart_item_model.CartItem).filter(
        cart_item_model.CartItem.id == cart_item_id).first()

    if not cart_item:
        raise exceptions.NotFoundException("Cart item not found.")

    db.delete(cart_item)
    db.commit()
