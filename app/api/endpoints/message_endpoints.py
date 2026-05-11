from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import message_service
from ...db.schemas import message_schema

message_router = APIRouter(prefix="/messages", tags=["Messages"])


@message_router.post("/", response_model=message_schema.MessageResponse)
def create_message(message_data: message_schema.MessageSchema, db: DBSession):
    return message_service.create_message(db, message_data)


@message_router.get("/", response_model=list[message_schema.MessageResponse])
def get_all_messages(db: DBSession):
    return message_service.get_all_messages(db)


@message_router.get("/{message_id}", response_model=message_schema.MessageResponse)
def get_message(message_id: str, db: DBSession):
    return message_service.get_message_by_id(db, message_id)


@message_router.get("/conversation/{conversation_id}", response_model=list[message_schema.MessageResponse])
def get_messages_by_conversation(conversation_id: str, db: DBSession):
    return message_service.get_messages_by_conversation_id(db, conversation_id)


@message_router.get("/whatsapp/{whatsapp_message_id}", response_model=message_schema.MessageResponse)
def get_message_by_whatsapp_id(whatsapp_message_id: str, db: DBSession):
    return message_service.get_message_by_whatsapp_message_id(db, whatsapp_message_id)


@message_router.put("/{message_id}", response_model=message_schema.MessageResponse)
def update_message(message_id: str, message_data: message_schema.MessageSchema, db: DBSession):
    return message_service.update_message(db, message_id, message_data)


@message_router.delete("/{message_id}", status_code=204)
def delete_message(message_id: str, db: DBSession):
    message_service.delete_message(db, message_id)
