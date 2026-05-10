from ..db.schemas import conversation_schema
from ..core import exceptions
from ..db.model import conversation_model
from sqlalchemy.orm import Session


def create_conversation(db: Session, conversation_data: conversation_schema.ConversationSchema) -> conversation_schema.ConversationResponse:
    new_conversation = conversation_model.Conversation(
        customer_id=conversation_data.customer_id,
        conversation_type=conversation_data.conversation_type,
        status=conversation_data.status
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
