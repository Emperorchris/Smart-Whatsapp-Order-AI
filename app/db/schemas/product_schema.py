from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class ProductSchema(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    sku: Optional[str] = None
    category: Optional[str] = None
    image_urls: Optional[List[str]] = None
    is_active: bool = True


class ProductResponse(ProductSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
