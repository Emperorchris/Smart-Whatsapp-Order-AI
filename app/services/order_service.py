from ..db.schemas import order_schema
from ..core import exceptions
from ..db.model import order_model
from sqlalchemy.orm import Session


def create_order(db: Session, order_data: order_schema.OrderSchema) -> order_schema.OrderResponse:
    existing = db.query(order_model.Order).filter(
        order_model.Order.order_number == order_data.order_number
    ).first()
    if existing:
        raise exceptions.ConflictException("An order with this order number already exists.")

    new_order = order_model.Order(
        customer_id=order_data.customer_id,
        order_number=order_data.order_number,
        customer_name=order_data.customer_name,
        customer_whatsapp_number=order_data.customer_whatsapp_number,
        status=order_data.status,
        total_amount=order_data.total_amount,
        payment_status=order_data.payment_status,
        delivery_address=order_data.delivery_address
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return order_schema.OrderResponse.model_validate(new_order)


def get_order_by_id(db: Session, order_id: str) -> order_schema.OrderResponse:
    order = db.query(order_model.Order).filter(
        order_model.Order.id == order_id).first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    return order_schema.OrderResponse.model_validate(order)


def get_all_orders(db: Session) -> list[order_schema.OrderResponse]:
    orders = db.query(order_model.Order).all()
    return [order_schema.OrderResponse.model_validate(o) for o in orders]


def get_order_by_order_number(db: Session, order_number: str) -> order_schema.OrderResponse:
    order = db.query(order_model.Order).filter(
        order_model.Order.order_number == order_number).first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    return order_schema.OrderResponse.model_validate(order)


def get_orders_by_customer_id(db: Session, customer_id: str) -> list[order_schema.OrderResponse]:
    orders = db.query(order_model.Order).filter(
        order_model.Order.customer_id == customer_id).all()
    return [order_schema.OrderResponse.model_validate(o) for o in orders]


def update_order(db: Session, order_id: str, order_data: order_schema.OrderSchema) -> order_schema.OrderResponse:
    order = db.query(order_model.Order).filter(
        order_model.Order.id == order_id).first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    is_number_taken = db.query(order_model.Order).filter(
        order_model.Order.order_number == order_data.order_number,
        order_model.Order.id != order_id
    ).first()
    if is_number_taken:
        raise exceptions.ConflictException("Order number is already taken by another order.")

    order.customer_id = order_data.customer_id
    order.order_number = order_data.order_number
    order.customer_name = order_data.customer_name
    order.customer_whatsapp_number = order_data.customer_whatsapp_number
    order.status = order_data.status
    order.total_amount = order_data.total_amount
    order.payment_status = order_data.payment_status
    order.delivery_address = order_data.delivery_address

    db.commit()
    db.refresh(order)

    return order_schema.OrderResponse.model_validate(order)


def delete_order(db: Session, order_id: str):
    order = db.query(order_model.Order).filter(
        order_model.Order.id == order_id).first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    db.delete(order)
    db.commit()
