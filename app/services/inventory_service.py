from ..db.schemas import inventory_schema
from ..core import exceptions
from ..db.model import inventory_model
from sqlalchemy.orm import Session


def create_inventory(db: Session, inventory_data: inventory_schema.InventorySchema) -> inventory_schema.InventoryResponse:
    existing = db.query(inventory_model.Inventory).filter(
        inventory_model.Inventory.product_id == inventory_data.product_id
    ).first()
    if existing:
        raise exceptions.ConflictException("Inventory for this product already exists.")

    new_inventory = inventory_model.Inventory(
        product_id=inventory_data.product_id,
        quantity_available=inventory_data.quantity_available,
        low_stock_threshold=inventory_data.low_stock_threshold
    )

    db.add(new_inventory)
    db.commit()
    db.refresh(new_inventory)

    return inventory_schema.InventoryResponse.model_validate(new_inventory)


def get_inventory_by_id(db: Session, inventory_id: str) -> inventory_schema.InventoryResponse:
    inventory = db.query(inventory_model.Inventory).filter(
        inventory_model.Inventory.id == inventory_id).first()

    if not inventory:
        raise exceptions.NotFoundException("Inventory not found.")

    return inventory_schema.InventoryResponse.model_validate(inventory)


def get_all_inventory(db: Session) -> list[inventory_schema.InventoryResponse]:
    items = db.query(inventory_model.Inventory).all()
    return [inventory_schema.InventoryResponse.model_validate(i) for i in items]


def get_inventory_by_product_id(db: Session, product_id: str) -> inventory_schema.InventoryResponse:
    inventory = db.query(inventory_model.Inventory).filter(
        inventory_model.Inventory.product_id == product_id).first()

    if not inventory:
        raise exceptions.NotFoundException("Inventory not found for this product.")

    return inventory_schema.InventoryResponse.model_validate(inventory)


def update_inventory(db: Session, inventory_id: str, inventory_data: inventory_schema.InventorySchema) -> inventory_schema.InventoryResponse:
    inventory = db.query(inventory_model.Inventory).filter(
        inventory_model.Inventory.id == inventory_id).first()

    if not inventory:
        raise exceptions.NotFoundException("Inventory not found.")

    is_product_taken = db.query(inventory_model.Inventory).filter(
        inventory_model.Inventory.product_id == inventory_data.product_id,
        inventory_model.Inventory.id != inventory_id
    ).first()
    if is_product_taken:
        raise exceptions.ConflictException("Inventory for this product already exists.")

    inventory.product_id = inventory_data.product_id
    inventory.quantity_available = inventory_data.quantity_available
    inventory.low_stock_threshold = inventory_data.low_stock_threshold

    db.commit()
    db.refresh(inventory)

    return inventory_schema.InventoryResponse.model_validate(inventory)


def delete_inventory(db: Session, inventory_id: str):
    inventory = db.query(inventory_model.Inventory).filter(
        inventory_model.Inventory.id == inventory_id).first()

    if not inventory:
        raise exceptions.NotFoundException("Inventory not found.")

    db.delete(inventory)
    db.commit()
