from datetime import datetime, timezone
import uuid
from sqlalchemy import JSON, UUID, Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from ..base import Base
from ...core import utils


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    order_id = Column(ForeignKey("orders.id", ondelete="CASCADE"))
    
    order = relationship("Order", back_populates="order_items")

    # product_id = Column(ForeignKey("products.id", ondelete="CASCADE"))
    product_id = Column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    
    variant_id = Column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)

    product_name = Column(String)
    
    product_sku = Column(String)
    
    product_description = Column(Text, nullable=True)
    
    product_category = Column(String, nullable=True)
    
    product_media = Column(JSON, nullable=True)
    
    product_variant_attributes = Column(JSON, nullable=True)

    quantity = Column(Integer)

    unit_price = Column(Numeric(12, 2))

    subtotal = Column(Numeric(12, 2))
    
    delivery_status = Column(String, default=utils.DeliveryStatus.PENDING.value)
    