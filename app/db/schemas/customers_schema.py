from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from uuid import UUID


class CustomerSchema(BaseModel):
    name: str
    whatsapp_number: str
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    extra_metadata: Optional[dict] = None  # For any additional customer info


class CustomerResponse(CustomerSchema):
    id: UUID
    name: str
    whatsapp_number: str
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    extra_metadata: Optional[dict] = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)
