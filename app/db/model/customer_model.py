from ..base import Base
from sqlalchemy import Column, String, DateTime, JSON, Uuid
from datetime import datetime, timezone
from ...core import utils

import uuid

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)
    name = Column(String, nullable=False)
    whatsapp_number = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    customer_type = Column(String, nullable=False, default=utils.CustomerType.INDIVIDUAL.value)
    customer_status = Column(String, nullable=False, default=utils.CustomerStatus.ACTIVE.value)
    customer_segment = Column(String, nullable=True, default=utils.CustomerSegment.NEW.value)
    extra_metadata = Column("metadata", JSON, nullable=True, default={})  # Store additional customer info
    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc), onupdate=datetime.now(tz=timezone.utc))