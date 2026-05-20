from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from ...core import utils

class OrderSchema(BaseModel):
    customer_id: UUID
    order_number: str
    customer_name: Optional[str] = None
    customer_whatsapp_number: Optional[str] = None
    status: str = utils.OrderStatus.PENDING.value
    total_amount: Decimal
    payment_status: str = utils.PaymentStatus.PENDING.value
    delivery_address: str
    extra_metadata: Optional[dict] = None  # For any additional order info


class OrderResponse(OrderSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
