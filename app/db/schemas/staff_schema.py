from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from ...core import utils


class StaffCreate(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    role: str = utils.StaffRole.SUPPORT.value
    password: str


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class StaffChangePassword(BaseModel):
    current_password: str
    new_password: str


class StaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime



class StaffLoginSchema(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    staff: StaffResponse
