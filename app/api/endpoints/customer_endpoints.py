from fastapi import APIRouter, Query
from ...core.dependencies import DBSession
from ...services import customer_service
from ...services.auth_service import CurrentStaff, AdminOnly
from ...db.schemas import customers_schema

customer_router = APIRouter(prefix="/customers", tags=["Customers"])


@customer_router.post("/", response_model=customers_schema.CustomerResponse)
async def create_customer(customer_data: customers_schema.CustomerSchema, db: DBSession, _: CurrentStaff):
    return await customer_service.create_customer(db, customer_data)


@customer_router.get("/", response_model=list[customers_schema.CustomerResponse])
async def get_all_customers(
    db: DBSession,
    _: CurrentStaff,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    return await customer_service.get_all_customers(db, skip=skip, limit=limit)


@customer_router.get("/{customer_id}", response_model=customers_schema.CustomerResponse)
async def get_customer(customer_id: str, db: DBSession, _: CurrentStaff):
    return await customer_service.get_customer_by_id(db, customer_id)


@customer_router.get("/whatsapp/{whatsapp_number}", response_model=customers_schema.CustomerResponse)
async def get_customer_by_whatsapp(whatsapp_number: str, db: DBSession, _: CurrentStaff):
    return await customer_service.get_customer_by_whatsapp_number(db, whatsapp_number)


@customer_router.put("/{customer_id}", response_model=customers_schema.CustomerResponse)
async def update_customer(customer_id: str, customer_data: customers_schema.CustomerSchema, db: DBSession, _: CurrentStaff):
    return await customer_service.update_customer(db, customer_id, customer_data)


@customer_router.delete("/{customer_id}", status_code=204)
async def delete_customer(customer_id: str, db: DBSession, _: AdminOnly):
    await customer_service.delete_customer(db, customer_id)
