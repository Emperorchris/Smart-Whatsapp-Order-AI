from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from ..base import Base
from ...core import utils
from ...core.config import Config

class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    order_id = Column(ForeignKey("orders.id"))

    payment_reference = Column(String, unique=True)

    amount = Column(Numeric(12, 2))

    currency = Column(String, default=Config.DEFAULT_CURRENCY)

    status = Column(String, default=utils.PaymentStatus.PENDING.value)
    # pending/success/failed

    payment_url = Column(Text, nullable=True)

    paid_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))