from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import payment_schema
from ..core import exceptions
from ..db.model import payment_model


async def create_payment(db: AsyncSession, payment_data: payment_schema.PaymentSchema) -> payment_schema.PaymentResponse:
    result = await db.execute(
        select(payment_model.Payment).filter(
            payment_model.Payment.payment_reference == payment_data.payment_reference
        )
    )
    if result.scalars().first():
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
    await db.commit()
    await db.refresh(new_payment)

    return payment_schema.PaymentResponse.model_validate(new_payment)


async def get_payment_by_id(db: AsyncSession, payment_id: str) -> payment_schema.PaymentResponse:
    result = await db.execute(
        select(payment_model.Payment).filter(payment_model.Payment.id == payment_id)
    )
    payment = result.scalars().first()

    if not payment:
        raise exceptions.NotFoundException("Payment not found.")

    return payment_schema.PaymentResponse.model_validate(payment)


async def get_all_payments(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[payment_schema.PaymentResponse]:
    result = await db.execute(
        select(payment_model.Payment).order_by(payment_model.Payment.created_at.desc()).offset(skip).limit(limit)
    )
    payments = result.scalars().all()
    return [payment_schema.PaymentResponse.model_validate(p) for p in payments]


async def get_payment_by_reference(db: AsyncSession, payment_reference: str) -> payment_schema.PaymentResponse:
    result = await db.execute(
        select(payment_model.Payment).filter(
            payment_model.Payment.payment_reference == payment_reference
        )
    )
    payment = result.scalars().first()

    if not payment:
        raise exceptions.NotFoundException("Payment not found.")

    return payment_schema.PaymentResponse.model_validate(payment)


async def get_payments_by_order_id(db: AsyncSession, order_id: str) -> list[payment_schema.PaymentResponse]:
    result = await db.execute(
        select(payment_model.Payment).filter(payment_model.Payment.order_id == order_id)
    )
    payments = result.scalars().all()
    return [payment_schema.PaymentResponse.model_validate(p) for p in payments]


async def update_payment(db: AsyncSession, payment_id: str, payment_data: payment_schema.PaymentSchema) -> payment_schema.PaymentResponse:
    result = await db.execute(
        select(payment_model.Payment).filter(payment_model.Payment.id == payment_id)
    )
    payment = result.scalars().first()

    if not payment:
        raise exceptions.NotFoundException("Payment not found.")

    dup_result = await db.execute(
        select(payment_model.Payment).filter(
            payment_model.Payment.payment_reference == payment_data.payment_reference,
            payment_model.Payment.id != payment_id
        )
    )
    if dup_result.scalars().first():
        raise exceptions.ConflictException("Payment reference is already taken by another payment.")

    payment.order_id = payment_data.order_id
    payment.payment_reference = payment_data.payment_reference
    payment.amount = payment_data.amount
    payment.currency = payment_data.currency
    payment.status = payment_data.status
    payment.payment_url = payment_data.payment_url

    await db.commit()
    await db.refresh(payment)

    return payment_schema.PaymentResponse.model_validate(payment)


async def delete_payment(db: AsyncSession, payment_id: str):
    result = await db.execute(
        select(payment_model.Payment).filter(payment_model.Payment.id == payment_id)
    )
    payment = result.scalars().first()

    if not payment:
        raise exceptions.NotFoundException("Payment not found.")

    await db.delete(payment)
    await db.commit()
