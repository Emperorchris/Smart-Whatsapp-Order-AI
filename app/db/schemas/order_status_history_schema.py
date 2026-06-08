from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class OrderStatusHistoryResponse(BaseModel):
    id: UUID
    order_id: UUID
    old_status: Optional[str] = None
    new_status: str
    changed_by_type: str
    changed_by_id: Optional[str] = None
    changed_by_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
