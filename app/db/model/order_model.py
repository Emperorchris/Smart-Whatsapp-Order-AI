from datetime import datetime, timezone
import uuid
from sqlalchemy import JSON, UUID, Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from ..base import Base
from ...core import utils


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    customer_id = Column(ForeignKey("customers.id", ondelete="CASCADE"))

    order_number = Column(String, unique=True)
    
    customer_name = Column(String, nullable=True)

    customer_whatsapp_number = Column(String, nullable=True)

    status = Column(String, default=utils.OrderStatus.PENDING.value)
    # pending/paid/shipped/completed/cancelled

    total_amount = Column(Numeric(12, 2))

    payment_status = Column(String, default=utils.PaymentStatus.PENDING.value)

    delivery_address = Column(Text)
    
    extra_metadata = Column(JSON, nullable=True)  # For any additional order info
    
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin")

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))