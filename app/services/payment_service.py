from ..db.schemas import payment_schema
from ..core import exceptions
from ..db.model import payment_model
from sqlalchemy.orm import Session


def create_payment(db: Session, payment_data: payment_schema.PaymentSchema) -> payment_schema.PaymentResponse:
    existing = db.query(payment_model.Payment).filter(
        payment_model.Payment.payment_reference == payment_data.payment_reference
    ).first()
    if existing:
        raise exceptions.ConflictException("A payment with this reference already exists.")

    new_payment = payment_model.Payment(
        order_id=payment_data.order_id,
        payment_reference=payment_data.payment_reference,
        amount=payment_data.amount,
        currency=payment_data.currency,
        status=payment_data.status,
        payment_url=payment_data.payment_url
    )

    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    return payment_schema.PaymentResponse.model_validate(new_payment)


def get_payment_by_id(db: Session, payment_id: str) -> payment_schema.PaymentResponse:
    payment = db.query(payment_model.Payment).filter(
        payment_model.Payment.id == payment_id).first()

    if not payment:
        raise exceptions.NotFoundException("Payment not found.")

    return payment_schema.PaymentResponse.model_validate(payment)


def get_all_payments(db: Session) -> list[payment_schema.PaymentResponse]:
    payments = db.query(payment_model.Payment).all()
    return [payment_schema.PaymentResponse.model_validate(p) for p in payments]


def get_payment_by_reference(db: Session, payment_reference: str) -> payment_schema.PaymentResponse:
    payment = db.query(payment_model.Payment).filter(
        payment_model.Payment.payment_reference == payment_reference).first()

    if not payment:
        raise exceptions.NotFoundException("Payment not found.")

    return payment_schema.PaymentResponse.model_validate(payment)


def get_payments_by_order_id(db: Session, order_id: str) -> list[payment_schema.PaymentResponse]:
    payments = db.query(payment_model.Payment).filter(
        payment_model.Payment.order_id == order_id).all()
    return [payment_schema.PaymentResponse.model_validate(p) for p in payments]


def update_payment(db: Session, payment_id: str, payment_data: payment_schema.PaymentSchema) -> payment_schema.PaymentResponse:
    payment = db.query(payment_model.Payment).filter(
        payment_model.Payment.id == payment_id).first()

    if not payment:
        raise exceptions.NotFoundException("Payment not found.")

    is_ref_taken = db.query(payment_model.Payment).filter(
        payment_model.Payment.payment_reference == payment_data.payment_reference,
        payment_model.Payment.id != payment_id
    ).first()
    if is_ref_taken:
        raise exceptions.ConflictException("Payment reference is already taken by another payment.")

    payment.order_id = payment_data.order_id
    payment.payment_reference = payment_data.payment_reference
    payment.amount = payment_data.amount
    payment.currency = payment_data.currency
    payment.status = payment_data.status
    payment.payment_url = payment_data.payment_url

    db.commit()
    db.refresh(payment)

    return payment_schema.PaymentResponse.model_validate(payment)


def delete_payment(db: Session, payment_id: str):
    payment = db.query(payment_model.Payment).filter(
        payment_model.Payment.id == payment_id).first()

    if not payment:
        raise exceptions.NotFoundException("Payment not found.")

    db.delete(payment)
    db.commit()
