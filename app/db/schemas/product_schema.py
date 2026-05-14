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
    category_id: Optional[UUID] = None
    image_urls: Optional[List[str]] = None
    live_image_urls: Optional[List[str]] = None
    video_urls: Optional[List[str]] = None
    live_video_urls: Optional[List[str]] = None
    is_active: bool = True
    
    
class ProductSearchParams(BaseModel):
    name: Optional[str] = None
    tracking_id: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    sku: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
