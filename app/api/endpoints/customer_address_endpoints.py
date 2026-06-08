from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import customer_address_service
from ...services.auth_service import CurrentStaff
from ...db.schemas import customer_address_schema

customer_address_router = APIRouter(prefix="/customer-addresses", tags=["Customer Addresses"])


@customer_address_router.post("/", response_model=customer_address_schema.CustomerAddressResponse)
async def create_address(address_data: customer_address_schema.CustomerAddressSchema, db: DBSession, _: CurrentStaff):
    return await customer_address_service.create_address(db, address_data)


@customer_address_router.get("/customer/{customer_id}", response_model=list[customer_address_schema.CustomerAddressResponse])
async def get_addresses_by_customer(customer_id: str, db: DBSession, _: CurrentStaff):
    return await customer_address_service.get_addresses_by_customer_id(db, customer_id)


@customer_address_router.get("/customer/{customer_id}/default", response_model=customer_address_schema.CustomerAddressResponse)
async def get_default_address(customer_id: str, db: DBSession, _: CurrentStaff):
    return await customer_address_service.get_default_address(db, customer_id)


@customer_address_router.get("/{address_id}", response_model=customer_address_schema.CustomerAddressResponse)
async def get_address(address_id: str, db: DBSession, _: CurrentStaff):
    return await customer_address_service.get_address_by_id(db, address_id)


@customer_address_router.put("/{address_id}", response_model=customer_address_schema.CustomerAddressResponse)
async def update_address(address_id: str, address_data: customer_address_schema.CustomerAddressSchema, db: DBSession, _: CurrentStaff):
    return await customer_address_service.update_address(db, address_id, address_data)


@customer_address_router.patch("/{address_id}/set-default", response_model=customer_address_schema.CustomerAddressResponse)
async def set_default_address(address_id: str, db: DBSession, _: CurrentStaff):
    return await customer_address_service.set_default_address(db, address_id)


@customer_address_router.delete("/{address_id}", status_code=204)
async def delete_address(address_id: str, db: DBSession, _: CurrentStaff):
    await customer_address_service.delete_address(db, address_id)
