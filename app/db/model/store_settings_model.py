from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, JSON, Uuid, Boolean
from ..base import Base


class StoreSettings(Base):
    __tablename__ = "store_settings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=True)
    description = Column(String, nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
