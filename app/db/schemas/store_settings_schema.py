from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


class StoreSettingSchema(BaseModel):
    key: str
    value: Any = None
    description: Optional[str] = None


class StoreSettingResponse(StoreSettingSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoreSettingsBulkUpdate(BaseModel):
    settings: list[StoreSettingSchema]
