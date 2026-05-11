from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import payment_service
from ...db.schemas import payment_schema

payment_router = APIRouter(prefix="/payments", tags=["Payments"])


@payment_router.post("/", response_model=payment_schema.PaymentResponse)
def create_payment(payment_data: payment_schema.PaymentSchema, db: DBSession):
    return payment_service.create_payment(db, payment_data)


@payment_router.get("/", response_model=list[payment_schema.PaymentResponse])
def get_all_payments(db: DBSession):
    return payment_service.get_all_payments(db)


@payment_router.get("/{payment_id}", response_model=payment_schema.PaymentResponse)
def get_payment(payment_id: str, db: DBSession):
    return payment_service.get_payment_by_id(db, payment_id)


@payment_router.get("/reference/{payment_reference}", response_model=payment_schema.PaymentResponse)
def get_payment_by_reference(payment_reference: str, db: DBSession):
    return payment_service.get_payment_by_reference(db, payment_reference)


@payment_router.get("/order/{order_id}", response_model=list[payment_schema.PaymentResponse])
def get_payments_by_order(order_id: str, db: DBSession):
    return payment_service.get_payments_by_order_id(db, order_id)


@payment_router.put("/{payment_id}", response_model=payment_schema.PaymentResponse)
def update_payment(payment_id: str, payment_data: payment_schema.PaymentSchema, db: DBSession):
    return payment_service.update_payment(db, payment_id, payment_data)


@payment_router.delete("/{payment_id}", status_code=204)
def delete_payment(payment_id: str, db: DBSession):
    payment_service.delete_payment(db, payment_id)
