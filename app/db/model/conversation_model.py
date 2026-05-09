from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid
from ..base import Base
from ...core import utils

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)
    customer_id = Column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    conversation_type = Column(String, nullable=False, default=utils.ConversationType.AI_KNOWLEDGE_BASED.value)
    status = Column(String, nullable=False, default=utils.ConversationStatus.ACTIVE.value)
    started_at = Column(DateTime, default=datetime.now(tz=timezone.utc))
    ended_at = Column(DateTime, nullable=True)