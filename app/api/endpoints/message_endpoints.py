from fastapi import APIRouter, Body, File, Form, UploadFile
from ...core.dependencies import DBSession
from ...core import utils
from ...services import message_service, voice_note_service
from ...services.auth_service import CurrentStaff, AdminOnly
from ...db.schemas import message_schema

message_router = APIRouter(prefix="/messages", tags=["Messages"])


@message_router.post("/", response_model=message_schema.MessageResponse)
async def create_message(message_data: message_schema.MessageSchema, db: DBSession, _: CurrentStaff):
    return await message_service.create_message(db, message_data)


@message_router.get("/", response_model=list[message_schema.MessageResponse])
async def get_all_messages(db: DBSession, _: CurrentStaff):
    return await message_service.get_all_messages(db)


@message_router.get("/{message_id}", response_model=message_schema.MessageResponse)
async def get_message(message_id: str, db: DBSession, _: CurrentStaff):
    return await message_service.get_message_by_id(db, message_id)


@message_router.get("/conversation/{conversation_id}", response_model=list[message_schema.MessageResponse])
async def get_messages_by_conversation(conversation_id: str, db: DBSession, _: CurrentStaff):
    return await message_service.get_messages_by_conversation_id(db, conversation_id)


@message_router.get("/whatsapp/{whatsapp_message_id}", response_model=message_schema.MessageResponse)
async def get_message_by_whatsapp_id(whatsapp_message_id: str, db: DBSession, _: CurrentStaff):
    return await message_service.get_message_by_whatsapp_message_id(db, whatsapp_message_id)


@message_router.put("/{message_id}", response_model=message_schema.MessageResponse)
async def update_message(message_id: str, message_data: message_schema.MessageSchema, db: DBSession, _: CurrentStaff):
    return await message_service.update_message(db, message_id, message_data)


@message_router.patch("/{message_id}/status", response_model=message_schema.MessageResponse)
async def update_message_status(
    message_id: str,
    db: DBSession,
    _: CurrentStaff,
    status: str = Body(..., embed=True),
):
    return await message_service.update_message_status(db, message_id, status)


@message_router.post("/voice")
async def send_voice_note(
    db: DBSession,
    _: CurrentStaff,
    customer_phone: str = Form(..., description="Customer WhatsApp number"),
    conversation_id: str = Form(..., description="Conversation ID to log the message under"),
    caption: str = Form(None, description="Optional text to send after the voice note"),
    file: UploadFile = File(..., description="Audio file (.ogg, .mp3, .m4a, .wav)"),
):
    """Send a voice note to a customer from the admin dashboard."""
    file_bytes = await file.read()
    return await voice_note_service.send_staff_voice_note(
        db=db,
        file_bytes=file_bytes,
        filename=file.filename or "",
        customer_phone=customer_phone,
        conversation_id=conversation_id,
        caption=caption,
    )


@message_router.delete("/{message_id}", status_code=204)
async def delete_message(message_id: str, db: DBSession, _: AdminOnly):
    await message_service.delete_message(db, message_id)
