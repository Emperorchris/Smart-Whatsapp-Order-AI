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
    address_label: Optional[str] = None
    address_full_name: Optional[str] = None
    address_phone_number: Optional[str] = None
    address_line: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_country: Optional[str] = "Nigeria"
    address_postal_code: Optional[str] = None
    address_landmark: Optional[str] = None
    extra_metadata: Optional[dict] = None


class OrderResponse(OrderSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkOrderStatusUpdate(BaseModel):
    order_ids: list[UUID]
    status: utils.OrderStatus


class BulkOrderStatusResponse(BaseModel):
    updated_count: int
    failed_ids: list[UUID]
    updated_orders: list[OrderResponse]
