from fastapi import APIRouter, Query
from ...core.dependencies import DBSession
from ...services import inventory_service
from ...services.auth_service import CurrentStaff, AdminOnly
from ...db.schemas import inventory_schema

inventory_router = APIRouter(prefix="/inventory", tags=["Inventory"])


@inventory_router.post("/", response_model=inventory_schema.InventoryResponse)
async def create_inventory(inventory_data: inventory_schema.InventorySchema, db: DBSession, _: AdminOnly):
    return await inventory_service.create_inventory(db, inventory_data)


@inventory_router.get("/", response_model=list[inventory_schema.InventoryResponse])
async def get_all_inventory(
    db: DBSession,
    _: CurrentStaff,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    return await inventory_service.get_all_inventory(db, skip=skip, limit=limit)


@inventory_router.get("/{inventory_id}", response_model=inventory_schema.InventoryResponse)
async def get_inventory(inventory_id: str, db: DBSession, _: CurrentStaff):
    return await inventory_service.get_inventory_by_id(db, inventory_id)


@inventory_router.get("/product/{product_id}", response_model=inventory_schema.InventoryResponse)
async def get_inventory_by_product(product_id: str, db: DBSession, _: CurrentStaff):
    return await inventory_service.get_inventory_by_product_id(db, product_id)


@inventory_router.put("/{inventory_id}", response_model=inventory_schema.InventoryResponse)
async def update_inventory(inventory_id: str, inventory_data: inventory_schema.InventorySchema, db: DBSession, _: AdminOnly):
    return await inventory_service.update_inventory(db, inventory_id, inventory_data)


@inventory_router.delete("/{inventory_id}", status_code=204)
async def delete_inventory(inventory_id: str, db: DBSession, _: AdminOnly):
    await inventory_service.delete_inventory(db, inventory_id)
