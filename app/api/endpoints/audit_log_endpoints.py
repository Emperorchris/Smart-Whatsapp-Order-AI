from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from ...core.dependencies import DBSession
from ...services import audit_log_service
from ...db.schemas import audit_log_schema

audit_router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@audit_router.get("/", response_model=audit_log_schema.PaginatedAuditLogResponse)
async def get_audit_logs(
    db: DBSession,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    staff_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return await audit_log_service.get_audit_logs(
        db, action, resource_type, staff_id, start_date, end_date, page, page_size
    )
