from ..base import Base
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, Uuid, ForeignKey, Float, Numeric
from datetime import datetime, timezone
import uuid


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)
    product_id = Column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    quantity_available = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=5)

    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc), onupdate=datetime.now(tz=timezone.utc))