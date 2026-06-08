from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..base import Base


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, index=True, unique=True)
    order_id = Column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)

    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)

    changed_by_type = Column(String, nullable=False, default="system")  # system/staff/customer
    changed_by_id = Column(String, nullable=True)
    changed_by_name = Column(String, nullable=True)

    notes = Column(Text, nullable=True)

    order = relationship("Order", back_populates="status_history")

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
