from datetime import datetime, timezone
import uuid
from sqlalchemy import Boolean, Column, String, DateTime, ForeignKey, Uuid
from ..base import Base


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    customer_id = Column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)

    label = Column(String, nullable=True)  # e.g. "Home", "Office", "Shop"
    full_name = Column(String, nullable=True)  # recipient name if different from customer
    phone_number = Column(String, nullable=True)  # delivery contact number
    address_line = Column(String, nullable=False)  # street address
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False, default="Nigeria")
    postal_code = Column(String, nullable=True)
    landmark = Column(String, nullable=True)  # nearby landmark for delivery riders

    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
