from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Column, Integer, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from ..base import Base
from ...core import utils


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    cart_id = Column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    
    cart = relationship("Cart", back_populates="cart_items")

    product_id = Column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)

    unit_price = Column(Numeric(12, 2))

    subtotal = Column(Numeric(12, 2))
    
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))