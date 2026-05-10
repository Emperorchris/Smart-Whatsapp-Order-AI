from ..db.schemas import message_schema
from ..core import exceptions
from ..db.model import message_model
from sqlalchemy.orm import Session


def create_message(db: Session, message_data: message_schema.MessageSchema) -> message_schema.MessageResponse:
    if message_data.whatsapp_message_id:
        existing = db.query(message_model.Message).filter(
            message_model.Message.whatsapp_message_id == message_data.whatsapp_message_id
        ).first()
        if existing:
            raise exceptions.ConflictException("A message with this WhatsApp message ID already exists.")

    new_message = message_model.Message(
        conversation_id=message_data.conversation_id,
        direction=message_data.direction,
        message_type=message_data.message_type,
        content=message_data.content,
        whatsapp_message_id=message_data.whatsapp_message_id
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return message_schema.MessageResponse.model_validate(new_message)


def get_message_by_id(db: Session, message_id: str) -> message_schema.MessageResponse:
    message = db.query(message_model.Message).filter(
        message_model.Message.id == message_id).first()

    if not message:
        raise exceptions.NotFoundException("Message not found.")

    return message_schema.MessageResponse.model_validate(message)


def get_all_messages(db: Session) -> list[message_schema.MessageResponse]:
    messages = db.query(message_model.Message).all()
    return [message_schema.MessageResponse.model_validate(m) for m in messages]


def get_messages_by_conversation_id(db: Session, conversation_id: str) -> list[message_schema.MessageResponse]:
    messages = db.query(message_model.Message).filter(
        message_model.Message.conversation_id == conversation_id).all()
    return [message_schema.MessageResponse.model_validate(m) for m in messages]


def get_message_by_whatsapp_message_id(db: Session, whatsapp_message_id: str) -> message_schema.MessageResponse:
    message = db.query(message_model.Message).filter(
        message_model.Message.whatsapp_message_id == whatsapp_message_id).first()

    if not message:
        raise exceptions.NotFoundException("Message not found.")

    return message_schema.MessageResponse.model_validate(message)


def update_message(db: Session, message_id: str, message_data: message_schema.MessageSchema) -> message_schema.MessageResponse:
    message = db.query(message_model.Message).filter(
        message_model.Message.id == message_id).first()

    if not message:
        raise exceptions.NotFoundException("Message not found.")

    if message_data.whatsapp_message_id:
        is_taken = db.query(message_model.Message).filter(
            message_model.Message.whatsapp_message_id == message_data.whatsapp_message_id,
            message_model.Message.id != message_id
        ).first()
        if is_taken:
            raise exceptions.ConflictException("WhatsApp message ID is already taken by another message.")

    message.conversation_id = message_data.conversation_id
    message.direction = message_data.direction
    message.message_type = message_data.message_type
    message.content = message_data.content
    message.whatsapp_message_id = message_data.whatsapp_message_id

    db.commit()
    db.refresh(message)

    return message_schema.MessageResponse.model_validate(message)


def delete_message(db: Session, message_id: str):
    message = db.query(message_model.Message).filter(
        message_model.Message.id == message_id).first()

    if not message:
        raise exceptions.NotFoundException("Message not found.")

    db.delete(message)
    db.commit()
