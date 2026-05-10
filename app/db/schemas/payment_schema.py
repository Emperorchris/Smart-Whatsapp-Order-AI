from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class PaymentSchema(BaseModel):
    order_id: UUID
    payment_reference: str
    amount: Decimal
    currency: str = "NGN"
    status: str = "pending"
    payment_url: Optional[str] = None


class PaymentResponse(PaymentSchema):
    id: UUID
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
