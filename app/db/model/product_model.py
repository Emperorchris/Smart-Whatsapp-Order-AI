from ..base import Base
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, Uuid, ForeignKey, Float, Numeric
from datetime import datetime, timezone
import uuid


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Numeric(12, 2))
    sku = Column(String, unique=True)
    category = Column(String, nullable=True)
    image_urls = Column(JSON, nullable=True)  # List of image URLs

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc), onupdate=datetime.now(tz=timezone.utc))