from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from ..base import Base
from ...core import utils


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    order_id = Column(ForeignKey("orders.id"))
    
    order = relationship("Order", back_populates="order_items")

    product_id = Column(ForeignKey("products.id"))

    product_name = Column(String)
    
    product_sku = Column(String)

    quantity = Column(Integer)

    unit_price = Column(Numeric(12, 2))

    subtotal = Column(Numeric(12, 2))