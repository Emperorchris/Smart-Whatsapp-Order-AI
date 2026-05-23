from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class CustomerAddressSchema(BaseModel):
    customer_id: UUID
    label: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    address_line: str
    city: str
    state: str
    country: str = "Nigeria"
    postal_code: Optional[str] = None
    landmark: Optional[str] = None
    is_default: bool = False


class CustomerAddressResponse(CustomerAddressSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
