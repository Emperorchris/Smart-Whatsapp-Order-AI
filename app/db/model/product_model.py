from ..base import Base
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, Uuid, ForeignKey, Float, Numeric
from datetime import datetime, timezone
import uuid


class Product(Base):
    __tablename__ = "products"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)
    tracking_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Numeric(12, 2))
    sku = Column(String, unique=True, nullable=True)
    category_id = Column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    image_urls = Column(JSON, nullable=True)  # List of image URLs
    video_urls = Column(JSON, nullable=True)  # List of video URLs
    
    live_image_urls = Column(JSON, nullable=True)  # List of live image URLs (e.g., from a live stream)
    live_video_urls = Column(JSON, nullable=True)  # List of live video URLs (e.g., from a live stream)
    
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc), onupdate=datetime.now(tz=timezone.utc))