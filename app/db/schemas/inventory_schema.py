from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class InventorySchema(BaseModel):
    product_id: UUID
    quantity_available: int = 0
    low_stock_threshold: int = 5


class InventoryResponse(InventorySchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
