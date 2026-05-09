from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from ..base import Base
from ...core import utils


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    customer_id = Column(ForeignKey("customers.id"))

    order_number = Column(String, unique=True)
    
    customer_name = Column(String, nullable=True)

    customer_whatsapp_number = Column(String, nullable=True)

    status = Column(String, default=utils.OrderStatus.PENDING.value)
    # pending/paid/shipped/completed/cancelled

    total_amount = Column(Numeric(12, 2))

    payment_status = Column(String, default=utils.PaymentStatus.PENDING.value)

    delivery_address = Column(Text)

    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc), onupdate=datetime.now(tz=timezone.utc))