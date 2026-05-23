from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import inventory_schema
from ..core import exceptions
from ..db.model import inventory_model


async def create_inventory(db: AsyncSession, inventory_data: inventory_schema.InventorySchema) -> inventory_schema.InventoryResponse:
    result = await db.execute(
        select(inventory_model.Inventory).filter(
            inventory_model.Inventory.product_id == inventory_data.product_id
        )
    )
    if result.scalars().first():
        raise exceptions.ConflictException("Inventory for this product already exists.")

    new_inventory = inventory_model.Inventory(
        product_id=inventory_data.product_id,
        quantity_available=inventory_data.quantity_available,
        low_stock_threshold=inventory_data.low_stock_threshold
    )

    db.add(new_inventory)
    await db.commit()
    await db.refresh(new_inventory)

    return inventory_schema.InventoryResponse.model_validate(new_inventory)


async def get_inventory_by_id(db: AsyncSession, inventory_id: str) -> inventory_schema.InventoryResponse:
    result = await db.execute(
        select(inventory_model.Inventory).filter(inventory_model.Inventory.id == inventory_id)
    )
    inventory = result.scalars().first()

    if not inventory:
        raise exceptions.NotFoundException("Inventory not found.")

    return inventory_schema.InventoryResponse.model_validate(inventory)


async def get_all_inventory(db: AsyncSession) -> list[inventory_schema.InventoryResponse]:
    result = await db.execute(select(inventory_model.Inventory))
    items = result.scalars().all()
    return [inventory_schema.InventoryResponse.model_validate(i) for i in items]


async def get_inventory_by_product_id(db: AsyncSession, product_id: str) -> inventory_schema.InventoryResponse:
    result = await db.execute(
        select(inventory_model.Inventory).filter(
            inventory_model.Inventory.product_id == product_id
        )
    )
    inventory = result.scalars().first()

    if not inventory:
        raise exceptions.NotFoundException("Inventory not found for this product.")

    return inventory_schema.InventoryResponse.model_validate(inventory)


async def update_inventory(db: AsyncSession, inventory_id: str, inventory_data: inventory_schema.InventorySchema) -> inventory_schema.InventoryResponse:
    result = await db.execute(
        select(inventory_model.Inventory).filter(inventory_model.Inventory.id == inventory_id)
    )
    inventory = result.scalars().first()

    if not inventory:
        raise exceptions.NotFoundException("Inventory not found.")

    dup_result = await db.execute(
        select(inventory_model.Inventory).filter(
            inventory_model.Inventory.product_id == inventory_data.product_id,
            inventory_model.Inventory.id != inventory_id
        )
    )
    if dup_result.scalars().first():
        raise exceptions.ConflictException("Inventory for this product already exists.")

    inventory.product_id = inventory_data.product_id
    inventory.quantity_available = inventory_data.quantity_available
    inventory.low_stock_threshold = inventory_data.low_stock_threshold

    await db.commit()
    await db.refresh(inventory)

    return inventory_schema.InventoryResponse.model_validate(inventory)


async def delete_inventory(db: AsyncSession, inventory_id: str):
    result = await db.execute(
        select(inventory_model.Inventory).filter(inventory_model.Inventory.id == inventory_id)
    )
    inventory = result.scalars().first()

    if not inventory:
        raise exceptions.NotFoundException("Inventory not found.")

    await db.delete(inventory)
    await db.commit()
