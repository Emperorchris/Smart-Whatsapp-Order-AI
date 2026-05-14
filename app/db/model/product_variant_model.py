from ..base import Base
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, Uuid, ForeignKey, Numeric
from datetime import datetime, timezone
import uuid


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)
    product_id = Column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    # sku = Column(String, unique=True, nullable=True)
    attributes = Column(JSON, nullable=False)  # e.g. {"size": "M", "color": "Red"}
    product_variant_price = Column(Numeric(12, 2), nullable=False)
    inventory_quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc), onupdate=datetime.now(tz=timezone.utc))
