from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from ...core import utils


class HumanHandOffSchema(BaseModel):
    conversation_id: UUID
    triggered_by: str = utils.HandOffTriggeredBy.AI.value
    reason: Optional[str] = None
    assigned_staff_id: Optional[UUID] = None
    status: str = utils.HandOffStatus.REQUESTED.value
    requested_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class StaffSummary(BaseModel):
    id: UUID
    name: str
    email: Optional[str] = None
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationSummary(BaseModel):
    id: UUID
    status: str
    ai_enabled: bool
    handoff_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HumanHandOffResponse(HumanHandOffSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime
    staff: Optional[StaffSummary] = None
    conversation: Optional[ConversationSummary] = None

    model_config = ConfigDict(from_attributes=True)
