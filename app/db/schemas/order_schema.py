from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class OrderSchema(BaseModel):
    customer_id: UUID
    order_number: str
    customer_name: Optional[str] = None
    customer_whatsapp_number: Optional[str] = None
    status: str = "pending"
    total_amount: Decimal
    payment_status: str = "pending"
    delivery_address: Optional[str] = None


class OrderResponse(OrderSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
