from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class CartItemSchema(BaseModel):
    cart_id: UUID
    product_id: UUID
    quantity: int = 1
    unit_price: Decimal
    subtotal: Decimal


class CartItemResponse(CartItemSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
