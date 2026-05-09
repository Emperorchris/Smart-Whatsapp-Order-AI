from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from ..base import Base
from ...core import utils

class ProcessedWebhook(Base):
    __tablename__ = "processed_webhooks"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    source = Column(String)
    # twilio/paystack

    event_id = Column(String, unique=True)

    processed_at = Column(DateTime, default=datetime.now(tz=timezone.utc))