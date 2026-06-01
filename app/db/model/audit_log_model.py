from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, JSON, Uuid, ForeignKey
from ..base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True, unique=True)

    staff_id = Column(ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    staff_name = Column(String, nullable=True)

    action = Column(String, nullable=False, index=True)  # e.g. "order.status_changed", "product.created"
    resource_type = Column(String, nullable=True, index=True)  # e.g. "order", "product", "handoff"
    resource_id = Column(String, nullable=True)

    details = Column(JSON, nullable=True)  # e.g. {"old_status": "pending", "new_status": "shipped"}

    ip_address = Column(String, nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc).replace(tzinfo=None))
