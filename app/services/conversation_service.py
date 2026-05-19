from ..db.schemas import conversation_schema
from ..core import exceptions
from ..db.model import conversation_model, staff_model, human_hand_off_model
from sqlalchemy.orm import Session
from ..core import utils
from datetime import datetime, timezone

def create_conversation(db: Session, conversation_data: conversation_schema.ConversationSchema) -> conversation_schema.ConversationResponse:
    new_conversation = conversation_model.Conversation(
        customer_id=conversation_data.customer_id,
        conversation_type=conversation_data.conversation_type,
        status=conversation_data.status,
        ai_enabled=conversation_data.ai_enabled if conversation_data.ai_enabled is not None else True,
        handoff_to_human=False,
        handoff_status=utils.HandOffStatus.NONE.value,
        assigned_staff_id=None,
    )

    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)

    return conversation_schema.ConversationResponse.model_validate(new_conversation)


def get_conversation_by_id(db: Session, conversation_id: str) -> conversation_schema.ConversationResponse:
    conversation = db.query(conversation_model.Conversation).filter(
        conversation_model.Conversation.id == conversation_id).first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")

    return conversation_schema.ConversationResponse.model_validate(conversation)


def get_all_conversations(db: Session) -> list[conversation_schema.ConversationResponse]:
    conversations = db.query(conversation_model.Conversation).all()
    return [conversation_schema.ConversationResponse.model_validate(c) for c in conversations]


def get_conversations_by_customer_id(db: Session, customer_id: str) -> list[conversation_schema.ConversationResponse]:
    conversations = db.query(conversation_model.Conversation).filter(
        conversation_model.Conversation.customer_id == customer_id).all()
    return [conversation_schema.ConversationResponse.model_validate(c) for c in conversations]


# def disable_ai(db: Session, conversation_id: str) -> conversation_schema.ConversationResponse:
#     conversation = db.query(conversation_model.Conversation).filter(
#         conversation_model.Conversation.id == conversation_id).first()

#     if not conversation:
#         raise exceptions.NotFoundException("Conversation not found.")

#     conversation.ai_enabled = False
#     conversation.handoff_to_human = True
    
#     db.commit()
#     db.refresh(conversation)

#     return conversation_schema.ConversationResponse.model_validate(conversation)


# def enable_ai(db: Session, conversation_id: str) -> conversation_schema.ConversationResponse:
#     conversation = db.query(conversation_model.Conversation).filter(
#         conversation_model.Conversation.id == conversation_id).first()

#     if not conversation:
#         raise exceptions.NotFoundException("Conversation not found.")

#     conversation.ai_enabled = True
#     conversation.handoff_to_human = False
    
#     db.commit()
#     db.refresh(conversation)

#     return conversation_schema.ConversationResponse.model_validate(conversation)


def start_handoff(db: Session, conversation_id: str, reason: str = None) -> conversation_schema.ConversationResponse:
    conversation = db.query(conversation_model.Conversation).filter(
        conversation_model.Conversation.id == conversation_id).first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")
    
    if conversation.handoff_to_human and conversation.handoff_status == utils.HandOffStatus.ACTIVE.value:
        raise exceptions.ConflictException("Handoff is already in progress for this conversation.")

    conversation.handoff_to_human = True
    conversation.ai_enabled = False
    conversation.assigned_staff_id = None
    conversation.handoff_status = utils.HandOffStatus.PENDING.value
    conversation.handoff_started_at = datetime.now(tz=timezone.utc) if not conversation.handoff_started_at else conversation.handoff_started_at
    conversation.handoff_ended_at = None
    conversation.handoff_reason = reason
    
    db.commit()
    db.refresh(conversation)

    return conversation_schema.ConversationResponse.model_validate(conversation)


def activate_handoff_for_staff(db: Session, conversation_id: str, staff_id: str) -> conversation_schema.ConversationResponse:
    conversation = db.query(conversation_model.Conversation).filter(
        conversation_model.Conversation.id == conversation_id).first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")
    
    staff = db.query(staff_model.Staff).filter(staff_model.Staff.id == staff_id).first()
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")

    conversation.handoff_to_human = True
    conversation.ai_enabled = False
    conversation.assigned_staff_id = staff.id
    conversation.handoff_status = utils.HandOffStatus.ACTIVE.value
    conversation.handoff_ended_at = None
    
    db.commit()
    db.refresh(conversation)
    
    return conversation_schema.ConversationResponse.model_validate(conversation)


def resume_ai(db: Session, conversation_id: str) -> conversation_schema.ConversationResponse:
    conversation = db.query(conversation_model.Conversation).filter(
        conversation_model.Conversation.id == conversation_id).first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")

    conversation.handoff_to_human = False
    conversation.ai_enabled = True
    conversation.assigned_staff_id = None
    conversation.handoff_status = utils.HandOffStatus.RESOLVED.value
    conversation.handoff_ended_at = datetime.now(tz=timezone.utc)
    conversation.handoff_reason = None

    # Close the active handoff record so both rows stay in sync
    active_handoff = db.query(human_hand_off_model.HumanHandOff).filter(
        human_hand_off_model.HumanHandOff.conversation_id == conversation_id,
        human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
    ).first()
    if active_handoff:
        active_handoff.status = utils.HandOffStatus.RESOLVED.value
        active_handoff.resolved_at = datetime.now(tz=timezone.utc)

    db.commit()
    db.refresh(conversation)

    return conversation_schema.ConversationResponse.model_validate(conversation)



def update_conversation(db: Session, conversation_id: str, conversation_data: conversation_schema.ConversationSchema) -> conversation_schema.ConversationResponse:
    conversation = db.query(conversation_model.Conversation).filter(
        conversation_model.Conversation.id == conversation_id).first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")

    conversation.customer_id = conversation_data.customer_id
    conversation.conversation_type = conversation_data.conversation_type
    conversation.status = conversation_data.status

    db.commit()
    db.refresh(conversation)

    return conversation_schema.ConversationResponse.model_validate(conversation)


def delete_conversation(db: Session, conversation_id: str):
    conversation = db.query(conversation_model.Conversation).filter(
        conversation_model.Conversation.id == conversation_id).first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")

    db.delete(conversation)
    db.commit()
