from datetime import date
from typing import Optional
from fastapi import APIRouter, Body, Query
from ...core.dependencies import DBSession
from ...services import conversation_service
from ...services.auth_service import CurrentStaff, AdminOnly
from ...db.schemas import conversation_schema, message_schema

conversation_router = APIRouter(prefix="/conversations", tags=["Conversations"])


@conversation_router.post("/", response_model=conversation_schema.ConversationResponse)
async def create_conversation(conversation_data: conversation_schema.ConversationSchema, db: DBSession, _: CurrentStaff):
    return await conversation_service.create_conversation(db, conversation_data)


@conversation_router.get("/", response_model=list[conversation_schema.ConversationResponse])
async def get_all_conversations(
    db: DBSession,
    _: CurrentStaff,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    return await conversation_service.get_all_conversations(db, skip=skip, limit=limit)


@conversation_router.get("/filter", response_model=conversation_schema.PaginatedConversationResponse)
async def get_filtered_conversations(
    db: DBSession,
    _: CurrentStaff,
    status: Optional[str] = None,
    handoff_status: Optional[str] = None,
    customer_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await conversation_service.get_filtered_conversations(
        db, status, handoff_status, customer_id, start_date, end_date, page, page_size
    )


@conversation_router.get("/{conversation_id}", response_model=conversation_schema.ConversationResponse)
async def get_conversation(conversation_id: str, db: DBSession, _: CurrentStaff):
    return await conversation_service.get_conversation_by_id(db, conversation_id)


@conversation_router.get("/customer/{customer_id}", response_model=list[conversation_schema.ConversationResponse])
async def get_conversations_by_customer(customer_id: str, db: DBSession, _: CurrentStaff):
    return await conversation_service.get_conversations_by_customer_id(db, customer_id)


@conversation_router.put("/{conversation_id}", response_model=conversation_schema.ConversationResponse)
async def update_conversation(conversation_id: str, conversation_data: conversation_schema.ConversationSchema, db: DBSession, _: CurrentStaff):
    return await conversation_service.update_conversation(db, conversation_id, conversation_data)


@conversation_router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, db: DBSession, _: AdminOnly):
    await conversation_service.delete_conversation(db, conversation_id)


# ── Handoff management (admin dashboard) ──────────────────────

@conversation_router.put("/{conversation_id}/handoff/start", response_model=conversation_schema.ConversationResponse)
async def start_handoff(
    conversation_id: str,
    db: DBSession,
    _: CurrentStaff,
    reason: Optional[str] = Body(None, embed=True),
):
    await conversation_service.start_handoff(db, conversation_id, reason=reason)
    return await conversation_service.get_conversation_by_id(db, conversation_id)


@conversation_router.put("/{conversation_id}/handoff/assign", response_model=conversation_schema.ConversationResponse)
async def assign_handoff_to_staff(
    conversation_id: str,
    db: DBSession,
    _: CurrentStaff,
    staff_id: str = Body(..., embed=True),
):
    await conversation_service.activate_handoff_for_staff(db, conversation_id, staff_id)
    return await conversation_service.get_conversation_by_id(db, conversation_id)


@conversation_router.put("/{conversation_id}/handoff/resume", response_model=conversation_schema.ConversationResponse)
async def resume_ai(conversation_id: str, db: DBSession, _: CurrentStaff):
    await conversation_service.resume_ai(db, conversation_id)
    return await conversation_service.get_conversation_by_id(db, conversation_id)


# ── Web dashboard → WhatsApp message relay ────────────────────

@conversation_router.post("/{conversation_id}/send", response_model=message_schema.MessageResponse)
async def send_message_from_dashboard(
    conversation_id: str,
    db: DBSession,
    _: CurrentStaff,
    text: str = Body(..., embed=True),
    staff_id: Optional[str] = Body(None, embed=True),
):
    return await conversation_service.send_message_from_dashboard(
        db, conversation_id, text, staff_id
    )
