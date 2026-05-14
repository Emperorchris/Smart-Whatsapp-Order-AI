from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class ProductVariantSchema(BaseModel):
    product_id: UUID
    # sku: str
    attributes: Dict[str, Any]  # e.g. {"size": "M", "color": "Red"}
    price: Decimal
    inventory_quantity: int = 0
    low_stock_threshold: int = 5
    is_active: bool = True


class ProductVariantResponse(ProductVariantSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


