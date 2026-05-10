from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class ConversationSchema(BaseModel):
    customer_id: UUID
    conversation_type: str
    status: str


class ConversationResponse(ConversationSchema):
    id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
