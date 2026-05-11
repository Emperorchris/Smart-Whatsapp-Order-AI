from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import customer_service
from ...db.schemas import customers_schema

customer_router = APIRouter(prefix="/customers", tags=["Customers"])


@customer_router.post("/", response_model=customers_schema.CustomerResponse)
def create_customer(customer_data: customers_schema.CustomerSchema, db: DBSession):
    return customer_service.create_customer(db, customer_data)


@customer_router.get("/{customer_id}", response_model=customers_schema.CustomerResponse)
def get_customer(customer_id: str, db: DBSession):
    return customer_service.get_customer_by_id(db, customer_id)


@customer_router.get("/whatsapp/{whatsapp_number}", response_model=customers_schema.CustomerResponse)
def get_customer_by_whatsapp(whatsapp_number: str, db: DBSession):
    return customer_service.get_customer_by_whatsapp_number(db, whatsapp_number)


@customer_router.put("/{customer_id}", response_model=customers_schema.CustomerResponse)
def update_customer(customer_id: str, customer_data: customers_schema.CustomerSchema, db: DBSession):
    return customer_service.update_customer(db, customer_id, customer_data)


@customer_router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: str, db: DBSession):
    customer_service.delete_customer(db, customer_id)
