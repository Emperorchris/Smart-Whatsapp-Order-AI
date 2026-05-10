from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from decimal import Decimal


class OrderItemSchema(BaseModel):
    order_id: UUID
    product_id: UUID
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderItemResponse(OrderItemSchema):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
