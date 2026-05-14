from ..db.schemas import human_hand_off_schema
from ..core import exceptions, utils
from ..db.model import human_hand_off_model
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from . import conversation_service, staff_service


def create_handoff(db: Session, data: human_hand_off_schema.HumanHandOffSchema) -> human_hand_off_schema.HumanHandOffResponse:
    new_handoff = human_hand_off_model.HumanHandOff(
        conversation_id=data.conversation_id,
        triggered_by=data.triggered_by,
        reason=data.reason,
        assigned_staff_id=data.assigned_staff_id,
        requested_at=datetime.now(tz=timezone.utc),
        status=data.status
    )

    db.add(new_handoff)
    db.commit()
    db.refresh(new_handoff)

    return human_hand_off_schema.HumanHandOffResponse.model_validate(new_handoff)


def get_handoffs_by_id(db: Session, handoff_id: str) -> human_hand_off_schema.HumanHandOffResponse:
    handoff = db.query(human_hand_off_model.HumanHandOff).filter(
        human_hand_off_model.HumanHandOff.id == handoff_id).first()

    if not handoff:
        raise exceptions.NotFoundException("Human hand-off record not found.")

    return human_hand_off_schema.HumanHandOffResponse.model_validate(handoff)


def get_handoffs_by_conversation_id(db: Session, conversation_id: str) -> list[human_hand_off_schema.HumanHandOffResponse]:
    handoffs = db.query(human_hand_off_model.HumanHandOff).filter(
        human_hand_off_model.HumanHandOff.conversation_id == conversation_id).all()
    if not handoffs:
        raise exceptions.NotFoundException("No human hand-off records found for this conversation.")
    
    return [human_hand_off_schema.HumanHandOffResponse.model_validate(handoff) for handoff in handoffs]

def get_handoffs_by_staff_id(db: Session, staff_id: str) -> list[human_hand_off_schema.HumanHandOffResponse]:
    handoffs = db.query(human_hand_off_model.HumanHandOff).filter(
        human_hand_off_model.HumanHandOff.assigned_staff_id == staff_id).all()
    if not handoffs:
        raise exceptions.NotFoundException("No human hand-off records found for this staff member.")
    
    return [human_hand_off_schema.HumanHandOffResponse.model_validate(handoff) for handoff in handoffs]


def get_active_handoffs(db: Session) -> list[human_hand_off_schema.HumanHandOffResponse]:
    handoffs = db.query(human_hand_off_model.HumanHandOff).filter(
        human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.REQUESTED.value).all()
    if not handoffs:
        raise exceptions.NotFoundException("No active human hand-off records found.")
    return [human_hand_off_schema.HumanHandOffResponse.model_validate(handoff) for handoff in handoffs]


def update_handoff_status(db: Session, handoff_id: str, new_status: utils.HandOffStatus) -> human_hand_off_schema.HumanHandOffResponse:
    handoff = db.query(human_hand_off_model.HumanHandOff).filter(
        human_hand_off_model.HumanHandOff.id == handoff_id).first()

    if not handoff:
        raise exceptions.NotFoundException("Human hand-off record not found.")

    if new_status not in [utils.HandOffStatus.REQUESTED, utils.HandOffStatus.ACTIVE, utils.HandOffStatus.RESOLVED]:
        raise exceptions.BadRequestException("Invalid status value.")

    handoff.status = new_status.value
    if new_status == utils.HandOffStatus.RESOLVED:
        handoff.resolved_at = datetime.now(tz=timezone.utc)

    db.commit()
    db.refresh(handoff)

    return human_hand_off_schema.HumanHandOffResponse.model_validate(handoff)


def assign_handoff_to_staff(db: Session, handoff_id: str, staff_id: str) -> human_hand_off_schema.HumanHandOffResponse:
    handoff = db.query(human_hand_off_model.HumanHandOff).filter(
        human_hand_off_model.HumanHandOff.id == handoff_id).first()

    if not handoff:
        raise exceptions.NotFoundException("Human hand-off record not found.")

    staff = staff_service.get_staff_by_id(db, staff_id)
    if not staff:
        raise exceptions.NotFoundException("Staff member not found for assignment.")
    
    handoff.assigned_staff_id = staff_id
    handoff.status = utils.HandOffStatus.ACTIVE.value
    db.commit()
    db.refresh(handoff)
    return human_hand_off_schema.HumanHandOffResponse.model_validate(handoff)


def delete_handoff(db: Session, handoff_id: str) -> None:
    handoff = db.query(human_hand_off_model.HumanHandOff).filter(
        human_hand_off_model.HumanHandOff.id == handoff_id).first()

    if not handoff:
        raise exceptions.NotFoundException("Human hand-off record not found.")

    db.delete(handoff)
    db.commit()
    
    