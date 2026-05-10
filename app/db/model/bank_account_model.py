from ..base import Base
from sqlalchemy import Column, String, Boolean, DateTime, Uuid
from datetime import datetime, timezone
import uuid


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc), onupdate=datetime.now(tz=timezone.utc))
