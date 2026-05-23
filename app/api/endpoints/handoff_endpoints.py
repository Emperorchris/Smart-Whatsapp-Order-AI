from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...core import utils
from ...services import human_handoff_service
from ...services.auth_service import CurrentStaff, AdminOnly
from ...db.schemas.human_hand_off_schema import HumanHandOffSchema, HumanHandOffResponse

handoff_router = APIRouter(prefix="/handoffs", tags=["Human Handoffs"])


@handoff_router.get("/", response_model=list[HumanHandOffResponse])
async def get_all_handoffs(db: DBSession, current_staff: AdminOnly):
    return await human_handoff_service.get_all_handoffs(db)


@handoff_router.get("/active", response_model=list[HumanHandOffResponse])
async def get_active_handoffs(db: DBSession, current_staff: CurrentStaff):
    return await human_handoff_service.get_active_handoffs(db)


@handoff_router.get("/pending", response_model=list[HumanHandOffResponse])
async def get_pending_handoffs(db: DBSession, current_staff: CurrentStaff):
    return await human_handoff_service.get_pending_handoffs(db)


@handoff_router.get("/me", response_model=HumanHandOffResponse)
async def get_my_active_handoff(db: DBSession, current_staff: CurrentStaff):
    return await human_handoff_service.get_staff_active_handoff(db, str(current_staff.id))


@handoff_router.get("/conversation/{conversation_id}", response_model=list[HumanHandOffResponse])
async def get_handoffs_by_conversation(conversation_id: str, db: DBSession, current_staff: CurrentStaff):
    return await human_handoff_service.get_handoffs_by_conversation_id(db, conversation_id)


@handoff_router.get("/staff/{staff_id}", response_model=list[HumanHandOffResponse])
async def get_handoffs_by_staff(staff_id: str, db: DBSession, current_staff: AdminOnly):
    return await human_handoff_service.get_handoffs_by_staff_id(db, staff_id)


@handoff_router.get("/{handoff_id}", response_model=HumanHandOffResponse)
async def get_handoff(handoff_id: str, db: DBSession, current_staff: CurrentStaff):
    return await human_handoff_service.get_handoffs_by_id(db, handoff_id)


@handoff_router.post("/claim", response_model=HumanHandOffResponse)
async def claim_next_handoff(db: DBSession, current_staff: CurrentStaff):
    return await human_handoff_service.claim_next_pending_handoff(db, str(current_staff.id))


@handoff_router.post("/{handoff_id}/assign", response_model=HumanHandOffResponse)
async def assign_handoff(handoff_id: str, staff_id: str, db: DBSession, current_staff: AdminOnly):
    return await human_handoff_service.assign_handoff_to_staff(db, handoff_id, staff_id)


@handoff_router.patch("/{handoff_id}/status", response_model=HumanHandOffResponse)
async def update_handoff_status(
    handoff_id: str,
    new_status: utils.HandOffStatus,
    db: DBSession,
    current_staff: CurrentStaff
):
    return await human_handoff_service.update_handoff_status(db, handoff_id, new_status)


@handoff_router.delete("/{handoff_id}", status_code=204)
async def delete_handoff(handoff_id: str, db: DBSession, current_staff: AdminOnly):
    await human_handoff_service.delete_handoff(db, handoff_id)
