from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid
from ..base import Base
from ...core import utils
from sqlalchemy.orm import relationship


class HumanHandOff(Base):
    __tablename__ = "human_hand_offs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)
    conversation_id = Column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    triggered_by = Column(String, nullable=False, default=utils.HandOffTriggeredBy.AI.value)
    reason = Column(String, nullable=True)
    assigned_staff_id = Column(
        ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    staff = relationship("Staff", back_populates="human_hand_offs", foreign_keys=[assigned_staff_id])
    conversation = relationship("Conversation", back_populates="human_hand_offs", foreign_keys=[conversation_id])
    status = Column(String, nullable=False, default=utils.HandOffStatus.REQUESTED.value)
    claimed_at = Column(DateTime, nullable=True)
    requested_at = Column(
        DateTime, nullable=False, default=datetime.now(tz=timezone.utc)
    )
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False,default=datetime.now(tz=timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now(tz=timezone.utc),
        onupdate=datetime.now(tz=timezone.utc),
    )
