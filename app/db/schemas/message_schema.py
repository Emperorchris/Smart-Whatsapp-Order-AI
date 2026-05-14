from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class MessageSchema(BaseModel):
    conversation_id: UUID
    sender_type: Optional[str] = None
    staff_id: Optional[UUID] = None
    direction: str
    message_type: str
    content: Optional[str] = None
    whatsapp_message_id: Optional[str] = None


class MessageResponse(MessageSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
