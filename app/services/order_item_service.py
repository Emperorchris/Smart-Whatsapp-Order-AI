from ..db.schemas import order_item_schema
from ..core import exceptions
from ..db.model import order_item_model
from sqlalchemy.orm import Session


def create_order_item(db: Session, order_item_data: order_item_schema.OrderItemSchema) -> order_item_schema.OrderItemResponse:
    new_order_item = order_item_model.OrderItem(
        order_id=order_item_data.order_id,
        product_id=order_item_data.product_id,
        product_name=order_item_data.product_name,
        product_sku=order_item_data.product_sku,
        quantity=order_item_data.quantity,
        unit_price=order_item_data.unit_price,
        subtotal=order_item_data.subtotal
    )

    db.add(new_order_item)
    db.commit()
    db.refresh(new_order_item)

    return order_item_schema.OrderItemResponse.model_validate(new_order_item)


def get_order_item_by_id(db: Session, order_item_id: str) -> order_item_schema.OrderItemResponse:
    order_item = db.query(order_item_model.OrderItem).filter(
        order_item_model.OrderItem.id == order_item_id).first()

    if not order_item:
        raise exceptions.NotFoundException("Order item not found.")

    return order_item_schema.OrderItemResponse.model_validate(order_item)


def get_all_order_items(db: Session) -> list[order_item_schema.OrderItemResponse]:
    items = db.query(order_item_model.OrderItem).all()
    return [order_item_schema.OrderItemResponse.model_validate(i) for i in items]


def get_order_items_by_order_id(db: Session, order_id: str) -> list[order_item_schema.OrderItemResponse]:
    items = db.query(order_item_model.OrderItem).filter(
        order_item_model.OrderItem.order_id == order_id).all()
    return [order_item_schema.OrderItemResponse.model_validate(i) for i in items]


def update_order_item(db: Session, order_item_id: str, order_item_data: order_item_schema.OrderItemSchema) -> order_item_schema.OrderItemResponse:
    order_item = db.query(order_item_model.OrderItem).filter(
        order_item_model.OrderItem.id == order_item_id).first()

    if not order_item:
        raise exceptions.NotFoundException("Order item not found.")

    order_item.order_id = order_item_data.order_id
    order_item.product_id = order_item_data.product_id
    order_item.product_name = order_item_data.product_name
    order_item.product_sku = order_item_data.product_sku
    order_item.quantity = order_item_data.quantity
    order_item.unit_price = order_item_data.unit_price
    order_item.subtotal = order_item_data.subtotal

    db.commit()
    db.refresh(order_item)

    return order_item_schema.OrderItemResponse.model_validate(order_item)


def delete_order_item(db: Session, order_item_id: str):
    order_item = db.query(order_item_model.OrderItem).filter(
        order_item_model.OrderItem.id == order_item_id).first()

    if not order_item:
        raise exceptions.NotFoundException("Order item not found.")

    db.delete(order_item)
    db.commit()
