from ..base import Base
from sqlalchemy import Column, String, DateTime, Boolean, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from ...core import utils


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4,
                index=True, unique=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone_number = Column(String, nullable=True)
    whatsapp_number = Column(String, unique=True, nullable=True)

    role = Column(String, nullable=False,
                  default=utils.StaffRole.SUPPORT.value)

    is_active = Column(Boolean, default=True)
    password_hash = Column(String, nullable=False)  # Store hashed passwords
    # Hashed refresh token; null when logged out
    refresh_token_hash = Column(String, nullable=True)
    human_hand_offs = relationship(
        "HumanHandOff", back_populates="staff", foreign_keys="HumanHandOff.assigned_staff_id", lazy="selectin")
    created_at = Column(DateTime, nullable=False,
                        default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
