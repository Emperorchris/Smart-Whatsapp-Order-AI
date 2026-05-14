from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from ...core import utils


class ConversationSchema(BaseModel):
    customer_id: UUID
    ai_enabled: bool = True
    handoff_to_human: bool = False
    handoff_status: Optional[str] = utils.HandOffStatus.NONE.value
    assigned_staff_id: Optional[UUID] = None
    handoff_reason: Optional[str] = None
    handoff_started_at: Optional[datetime] = None
    handoff_ended_at: Optional[datetime] = None
    conversation_type: utils.ConversationType = utils.ConversationType.AI_KNOWLEDGE_BASED.value
    status: utils.ConversationStatus = utils.ConversationStatus.ACTIVE.value


class ConversationResponse(ConversationSchema):
    id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
