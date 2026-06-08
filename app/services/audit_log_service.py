from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.model.audit_log_model import AuditLog
from ..db.schemas import audit_log_schema


async def log_action(
    db: AsyncSession,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    staff_id: str | None = None,
    staff_name: str | None = None,
    ip_address: str | None = None,
):
    """Persist a single audit log entry for a staff or system action."""
    entry = AuditLog(
        staff_id=staff_id,
        staff_name=staff_name,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.commit()


async def get_audit_logs(
    db: AsyncSession,
    action: str | None = None,
    resource_type: str | None = None,
    staff_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> audit_log_schema.PaginatedAuditLogResponse:
    """Return paginated audit logs filtered by action, resource, staff, or date range."""
    base = select(AuditLog)
    count_q = select(func.count(AuditLog.id))

    if action:
        base = base.where(AuditLog.action == action)
        count_q = count_q.where(AuditLog.action == action)
    if resource_type:
        base = base.where(AuditLog.resource_type == resource_type)
        count_q = count_q.where(AuditLog.resource_type == resource_type)
    if staff_id:
        base = base.where(AuditLog.staff_id == staff_id)
        count_q = count_q.where(AuditLog.staff_id == staff_id)
    if start_date:
        dt = datetime.combine(start_date, datetime.min.time())
        base = base.where(AuditLog.created_at >= dt)
        count_q = count_q.where(AuditLog.created_at >= dt)
    if end_date:
        dt = datetime.combine(end_date, datetime.max.time())
        base = base.where(AuditLog.created_at <= dt)
        count_q = count_q.where(AuditLog.created_at <= dt)

    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(
        base.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    return audit_log_schema.PaginatedAuditLogResponse(
        items=[audit_log_schema.AuditLogResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
