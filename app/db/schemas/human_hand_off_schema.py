from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class HumanHandOffSchema(BaseModel):
    pass


class HumanHandOffResponse(BaseModel):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
