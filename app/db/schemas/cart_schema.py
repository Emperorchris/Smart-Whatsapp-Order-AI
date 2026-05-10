from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class CartSchema(BaseModel):
    customer_id: UUID
    status: str = "active"


class CartResponse(CartSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
