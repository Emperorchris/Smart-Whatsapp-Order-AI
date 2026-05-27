from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from ..db.schemas import human_hand_off_schema
from ..core import exceptions, utils
from ..db.model import human_hand_off_model
from . import staff_service


async def create_handoff(db: AsyncSession, data: human_hand_off_schema.HumanHandOffSchema) -> human_hand_off_schema.HumanHandOffResponse:
    # Check if there's an existing unresolved handoff for this conversation
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.conversation_id == data.conversation_id,
            human_hand_off_model.HumanHandOff.status.in_([
                utils.HandOffStatus.PENDING.value,
                utils.HandOffStatus.ACTIVE.value,
                utils.HandOffStatus.REQUESTED.value,
            ])
        )
    )
    existing_handoff = result.scalars().first()
    
    if existing_handoff:
        raise exceptions.BadRequestException(
            f"Cannot initiate a new handoff. You already have a handoff with status '{existing_handoff.status}' for this conversation. Please resolve or cancel the existing handoff before creating a new one."
        )
    
    new_handoff = human_hand_off_model.HumanHandOff(
        conversation_id=data.conversation_id,
        triggered_by=data.triggered_by,
        reason=data.reason,
        assigned_staff_id=data.assigned_staff_id,
        requested_at=datetime.now(tz=timezone.utc).replace(tzinfo=None),
        status=utils.HandOffStatus.PENDING.value
    )

    db.add(new_handoff)
    await db.commit()
    await db.refresh(new_handoff)

    return human_hand_off_schema.HumanHandOffResponse.model_validate(new_handoff)


async def cancel_handoff(db: AsyncSession, handoff_id: str) -> human_hand_off_schema.HumanHandOffResponse:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.id == handoff_id
        )
    )
    handoff = result.scalars().first()

    if not handoff:
        raise exceptions.NotFoundException("Human hand-off record not found.")

    if handoff.status == utils.HandOffStatus.RESOLVED.value:
        raise exceptions.BadRequestException("Cannot cancel a resolved hand-off.")

    if handoff.status == utils.HandOffStatus.CANCELLED.value:
        raise exceptions.BadRequestException("This hand-off is already cancelled.")

    handoff.status = utils.HandOffStatus.CANCELLED.value
    await db.commit()
    await db.refresh(handoff)
    return human_hand_off_schema.HumanHandOffResponse.model_validate(handoff)


async def check_handoff_status(db: AsyncSession, conversation_id: str) -> str:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.conversation_id == conversation_id,
            human_hand_off_model.HumanHandOff.status.in_([
                utils.HandOffStatus.PENDING.value,
                utils.HandOffStatus.ACTIVE.value,
                utils.HandOffStatus.REQUESTED.value,
            ])
        ).order_by(human_hand_off_model.HumanHandOff.requested_at.desc())
    )
    handoff = result.scalars().first()

    if not handoff:
        return "No active hand-off requests for this conversation."

    return f"Current hand-off status: {handoff.status}. Triggered by: {handoff.triggered_by}. Reason: {handoff.reason or 'N/A'}."




async def get_all_handoffs(db: AsyncSession) -> list[human_hand_off_schema.HumanHandOffResponse]:
    result = await db.execute(select(human_hand_off_model.HumanHandOff))
    handoffs = result.scalars().all()
    return [human_hand_off_schema.HumanHandOffResponse.model_validate(h) for h in handoffs]


async def get_handoffs_by_id(db: AsyncSession, handoff_id: str) -> human_hand_off_schema.HumanHandOffResponse:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.id == handoff_id
        )
    )
    handoff = result.scalars().first()

    if not handoff:
        raise exceptions.NotFoundException("Human hand-off record not found.")

    return human_hand_off_schema.HumanHandOffResponse.model_validate(handoff)


async def get_handoffs_by_conversation_id(db: AsyncSession, conversation_id: str) -> list[human_hand_off_schema.HumanHandOffResponse]:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.conversation_id == conversation_id
        )
    )
    handoffs = result.scalars().all()
    return [human_hand_off_schema.HumanHandOffResponse.model_validate(h) for h in handoffs]


async def get_handoffs_by_staff_id(db: AsyncSession, staff_id: str) -> list[human_hand_off_schema.HumanHandOffResponse]:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff_id
        )
    )
    handoffs = result.scalars().all()
    return [human_hand_off_schema.HumanHandOffResponse.model_validate(h) for h in handoffs]


async def get_active_handoffs(db: AsyncSession) -> list[human_hand_off_schema.HumanHandOffResponse]:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value
        )
    )
    handoffs = result.scalars().all()
    if not handoffs:
        raise exceptions.NotFoundException("No active human hand-off records found.")
    return [human_hand_off_schema.HumanHandOffResponse.model_validate(h) for h in handoffs]


async def get_pending_handoffs(db: AsyncSession) -> list[human_hand_off_schema.HumanHandOffResponse]:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.PENDING.value
        ).order_by(human_hand_off_model.HumanHandOff.requested_at.asc())
    )
    handoffs = result.scalars().all()

    if not handoffs:
        raise exceptions.NotFoundException("No pending human hand-off records found.")

    return [human_hand_off_schema.HumanHandOffResponse.model_validate(h) for h in handoffs]


async def update_handoff_status(db: AsyncSession, handoff_id: str, new_status: utils.HandOffStatus) -> human_hand_off_schema.HumanHandOffResponse:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.id == handoff_id
        )
    )
    handoff = result.scalars().first()

    if not handoff:
        raise exceptions.NotFoundException("Human hand-off record not found.")

    if new_status not in [
        utils.HandOffStatus.PENDING,
        utils.HandOffStatus.REQUESTED,
        utils.HandOffStatus.ACTIVE,
        utils.HandOffStatus.RESOLVED,
    ]:
        raise exceptions.BadRequestException("Invalid status value.")

    handoff.status = new_status.value
    if new_status == utils.HandOffStatus.ACTIVE and not handoff.claimed_at:
        handoff.claimed_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
    if new_status == utils.HandOffStatus.RESOLVED:
        handoff.resolved_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(handoff)

    return human_hand_off_schema.HumanHandOffResponse.model_validate(handoff)


async def assign_handoff_to_staff(db: AsyncSession, handoff_id: str, staff_id: str) -> human_hand_off_schema.HumanHandOffResponse:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.id == handoff_id
        )
    )
    handoff = result.scalars().first()

    if not handoff:
        raise exceptions.NotFoundException("Human hand-off record not found.")

    staff = await staff_service.get_staff_by_id(db, staff_id)
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")

    if not staff.is_active:
        raise exceptions.ForbiddenException("Cannot assign hand-off to an inactive staff member.")

    if handoff.status not in [utils.HandOffStatus.PENDING.value, utils.HandOffStatus.REQUESTED.value]:
        raise exceptions.BadRequestException("Only pending/requested hand-offs can be assigned.")

    active_result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff_id,
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
        )
    )
    if active_result.scalars().first():
        raise exceptions.ConflictException("Staff already has an active hand-off.")

    handoff.assigned_staff_id = staff_id
    handoff.status = utils.HandOffStatus.ACTIVE.value
    handoff.claimed_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(handoff)
    return human_hand_off_schema.HumanHandOffResponse.model_validate(handoff)


async def get_staff_active_handoff(db: AsyncSession, staff_id: str) -> human_hand_off_schema.HumanHandOffResponse:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff_id,
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
        ).order_by(human_hand_off_model.HumanHandOff.claimed_at.desc())
    )
    handoff = result.scalars().first()

    if not handoff:
        raise exceptions.NotFoundException("Staff has no active hand-off.")

    return human_hand_off_schema.HumanHandOffResponse.model_validate(handoff)


async def claim_next_pending_handoff(db: AsyncSession, staff_id: str) -> human_hand_off_schema.HumanHandOffResponse:
    staff = await staff_service.get_staff_by_id(db, staff_id)
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")
    if not staff.is_active:
        raise exceptions.ForbiddenException("Account is inactive.")

    existing_result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff_id,
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
        )
    )
    if existing_result.scalars().first():
        raise exceptions.ConflictException(
            f"You already have an active hand-off. Use {utils.StaffConversationCommand.DONE.value} to mark it as done or or {utils.StaffConversationCommand.SKIP.value} to skip before claiming the next one."
        )

    pending_result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.status.in_([
                utils.HandOffStatus.PENDING.value,
                utils.HandOffStatus.REQUESTED.value,
            ])
        ).order_by(human_hand_off_model.HumanHandOff.requested_at.asc())
    )
    handoff = pending_result.scalars().first()

    if not handoff:
        raise exceptions.NotFoundException("No pending hand-offs available.")

    handoff.assigned_staff_id = staff_id
    handoff.status = utils.HandOffStatus.ACTIVE.value
    handoff.claimed_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(handoff)

    return human_hand_off_schema.HumanHandOffResponse.model_validate(handoff)


async def delete_handoff(db: AsyncSession, handoff_id: str) -> None:
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.id == handoff_id
        )
    )
    handoff = result.scalars().first()

    if not handoff:
        raise exceptions.NotFoundException("Human hand-off record not found.")

    await db.delete(handoff)
    await db.commit()
