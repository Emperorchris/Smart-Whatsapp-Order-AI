from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class ProcessedWebhookSchema(BaseModel):
    source: str
    event_id: str


class ProcessedWebhookResponse(ProcessedWebhookSchema):
    id: UUID
    processed_at: datetime

    model_config = ConfigDict(from_attributes=True)
