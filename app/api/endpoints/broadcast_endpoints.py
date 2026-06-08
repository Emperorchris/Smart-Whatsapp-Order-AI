from typing import Optional
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from ...core.dependencies import DBSession
from ...services import broadcast_service
from ...services.auth_service import AdminOnly

broadcast_router = APIRouter(prefix="/broadcast", tags=["Broadcast"])


class BroadcastRequest(BaseModel):
    message: str
    segment: Optional[str] = None
    customer_ids: Optional[list[UUID]] = None


@broadcast_router.post("/")
async def send_broadcast(data: BroadcastRequest, db: DBSession, _: AdminOnly):
    result = await broadcast_service.broadcast_message(
        db,
        message=data.message,
        segment=data.segment,
        customer_ids=[str(cid) for cid in data.customer_ids] if data.customer_ids else None,
    )
    return result
