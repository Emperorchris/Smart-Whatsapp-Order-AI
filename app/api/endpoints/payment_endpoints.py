from fastapi import APIRouter, Query
from ...core.dependencies import DBSession
from ...services import payment_service
from ...services.auth_service import CurrentStaff, AdminOnly
from ...db.schemas import payment_schema

payment_router = APIRouter(prefix="/payments", tags=["Payments"])


@payment_router.post("/", response_model=payment_schema.PaymentResponse)
async def create_payment(payment_data: payment_schema.PaymentSchema, db: DBSession, _: CurrentStaff):
    return await payment_service.create_payment(db, payment_data)


@payment_router.get("/", response_model=list[payment_schema.PaymentResponse])
async def get_all_payments(
    db: DBSession,
    _: CurrentStaff,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    return await payment_service.get_all_payments(db, skip=skip, limit=limit)


@payment_router.get("/{payment_id}", response_model=payment_schema.PaymentResponse)
async def get_payment(payment_id: str, db: DBSession, _: CurrentStaff):
    return await payment_service.get_payment_by_id(db, payment_id)


@payment_router.get("/reference/{payment_reference}", response_model=payment_schema.PaymentResponse)
async def get_payment_by_reference(payment_reference: str, db: DBSession, _: CurrentStaff):
    return await payment_service.get_payment_by_reference(db, payment_reference)


@payment_router.get("/order/{order_id}", response_model=list[payment_schema.PaymentResponse])
async def get_payments_by_order(order_id: str, db: DBSession, _: CurrentStaff):
    return await payment_service.get_payments_by_order_id(db, order_id)


@payment_router.put("/{payment_id}", response_model=payment_schema.PaymentResponse)
async def update_payment(payment_id: str, payment_data: payment_schema.PaymentSchema, db: DBSession, _: CurrentStaff):
    return await payment_service.update_payment(db, payment_id, payment_data)


@payment_router.delete("/{payment_id}", status_code=204)
async def delete_payment(payment_id: str, db: DBSession, _: AdminOnly):
    await payment_service.delete_payment(db, payment_id)
