from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Boolean
from sqlalchemy.orm import relationship
from ..base import Base
from ...core import utils


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4,
                index=True, unique=True)
    customer_id = Column(ForeignKey(
        "customers.id", ondelete="CASCADE"), nullable=False)
    ai_enabled = Column(Boolean, default=True)
    handoff_to_human = Column(Boolean, default=False)
    handoff_status = Column(String, nullable=True,
                            default=utils.HandOffStatus.NONE.value)
    assigned_staff_id = Column(ForeignKey(
        "staff.id", ondelete="SET NULL"), nullable=True)
    handoff_reason = Column(String, nullable=True)
    conversation_type = Column(
        String, nullable=False, default=utils.ConversationType.AI_KNOWLEDGE_BASED.value)
    status = Column(String, nullable=False,
                    default=utils.ConversationStatus.ACTIVE.value)
    started_at = Column(DateTime, default=datetime.now(tz=timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    handoff_started_at = Column(DateTime, nullable=True)
    handoff_ended_at = Column(DateTime, nullable=True)
    human_hand_offs = relationship(
        "HumanHandOff", back_populates="conversation", foreign_keys="HumanHandOff.conversation_id")
