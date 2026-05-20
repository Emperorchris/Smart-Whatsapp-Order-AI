from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Column, String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from ..base import Base
from ...core import utils


class Cart(Base):
    __tablename__ = "carts"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    customer_id = Column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    cart_items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    status = Column(String, default=utils.CartStatus.ACTIVE.value)
    # active/checked_out/abandoned

    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc), onupdate=datetime.now(tz=timezone.utc))