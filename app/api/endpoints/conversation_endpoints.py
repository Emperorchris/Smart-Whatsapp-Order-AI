from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import conversation_service
from ...db.schemas import conversation_schema

conversation_router = APIRouter(prefix="/conversations", tags=["Conversations"])


@conversation_router.post("/", response_model=conversation_schema.ConversationResponse)
def create_conversation(conversation_data: conversation_schema.ConversationSchema, db: DBSession):
    return conversation_service.create_conversation(db, conversation_data)


@conversation_router.get("/", response_model=list[conversation_schema.ConversationResponse])
def get_all_conversations(db: DBSession):
    return conversation_service.get_all_conversations(db)


@conversation_router.get("/{conversation_id}", response_model=conversation_schema.ConversationResponse)
def get_conversation(conversation_id: str, db: DBSession):
    return conversation_service.get_conversation_by_id(db, conversation_id)


@conversation_router.get("/customer/{customer_id}", response_model=list[conversation_schema.ConversationResponse])
def get_conversations_by_customer(customer_id: str, db: DBSession):
    return conversation_service.get_conversations_by_customer_id(db, customer_id)


@conversation_router.put("/{conversation_id}", response_model=conversation_schema.ConversationResponse)
def update_conversation(conversation_id: str, conversation_data: conversation_schema.ConversationSchema, db: DBSession):
    return conversation_service.update_conversation(db, conversation_id, conversation_data)


@conversation_router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, db: DBSession):
    conversation_service.delete_conversation(db, conversation_id)
