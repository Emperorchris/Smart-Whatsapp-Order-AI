from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Text, JSON
from ..base import Base
from ...core import utils


class Message(Base):
    __tablename__ = "messages"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4,
                index=True, unique=True)
    conversation_id = Column(ForeignKey("conversations.id", ondelete="CASCADE"))
    sender_type = Column(String, nullable=True,
                         default=utils.MessageSenderType.CUSTOMER.value)
    staff_id = Column(ForeignKey(
        "staff.id", ondelete="SET NULL"), nullable=True)
    direction = Column(String, nullable=False,
                       default=utils.MessageDirection.INBOUND.value)
    message_type = Column(String, nullable=False,
                          default=utils.MessageType.TEXT.value)
    content = Column(Text)
    media_urls = Column(JSON, nullable=True)
    tool_metadata = Column(JSON, nullable=True)
    status = Column(String, nullable=True, default=utils.MessageStatus.SENT.value)
    whatsapp_message_id = Column(String, unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
