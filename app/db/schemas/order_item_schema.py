from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from uuid import UUID
from decimal import Decimal


class OrderItemSchema(BaseModel):
    order_id: UUID
    product_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_description: Optional[str] = None
    product_category: Optional[str] = None
    product_media: Optional[list[dict[str, Any]]] = None
    product_variant_attributes: Optional[dict[str, Any]] = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    delivery_status: Optional[str] = None


class OrderItemResponse(OrderItemSchema):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
