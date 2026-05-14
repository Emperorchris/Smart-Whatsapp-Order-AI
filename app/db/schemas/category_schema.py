from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class CategorySchema(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    is_active: bool = True


class CategoryResponse(CategorySchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
