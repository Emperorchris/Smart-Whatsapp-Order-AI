from ..base import Base
from sqlalchemy import Column, String, Text, DateTime, Boolean, Uuid, ForeignKey
from datetime import datetime, timezone
import uuid


class Category(Base):
    __tablename__ = "categories"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc), onupdate=datetime.now(tz=timezone.utc))
