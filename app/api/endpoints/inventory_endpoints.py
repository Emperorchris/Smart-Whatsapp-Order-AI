from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import inventory_service
from ...db.schemas import inventory_schema

inventory_router = APIRouter(prefix="/inventory", tags=["Inventory"])


@inventory_router.post("/", response_model=inventory_schema.InventoryResponse)
def create_inventory(inventory_data: inventory_schema.InventorySchema, db: DBSession):
    return inventory_service.create_inventory(db, inventory_data)


@inventory_router.get("/", response_model=list[inventory_schema.InventoryResponse])
def get_all_inventory(db: DBSession):
    return inventory_service.get_all_inventory(db)


@inventory_router.get("/{inventory_id}", response_model=inventory_schema.InventoryResponse)
def get_inventory(inventory_id: str, db: DBSession):
    return inventory_service.get_inventory_by_id(db, inventory_id)


@inventory_router.get("/product/{product_id}", response_model=inventory_schema.InventoryResponse)
def get_inventory_by_product(product_id: str, db: DBSession):
    return inventory_service.get_inventory_by_product_id(db, product_id)


@inventory_router.put("/{inventory_id}", response_model=inventory_schema.InventoryResponse)
def update_inventory(inventory_id: str, inventory_data: inventory_schema.InventorySchema, db: DBSession):
    return inventory_service.update_inventory(db, inventory_id, inventory_data)


@inventory_router.delete("/{inventory_id}", status_code=204)
def delete_inventory(inventory_id: str, db: DBSession):
    inventory_service.delete_inventory(db, inventory_id)
