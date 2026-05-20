from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from ...core import utils
from . import cart_item_schema


class CartSchema(BaseModel):
    customer_id: UUID
    status: str = "active"


class CartResponse(CartSchema):
    id: UUID
    cart_items: Optional[list[cart_item_schema.CartItemResponse]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartAction(BaseModel):
    action: utils.CartActionType
    product_name: Optional[str] = None
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    quantity: int = 1
