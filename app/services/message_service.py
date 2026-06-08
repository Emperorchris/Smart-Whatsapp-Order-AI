from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import message_schema
from ..core import exceptions, utils
from ..db.model import message_model
from . import websocket_service


async def create_message(
    db: AsyncSession, message_data: message_schema.MessageSchema
) -> message_schema.MessageResponse:
    if message_data.whatsapp_message_id:
        result = await db.execute(
            select(message_model.Message).filter(
                message_model.Message.whatsapp_message_id
                == message_data.whatsapp_message_id
            )
        )
        if result.scalars().first():
            raise exceptions.ConflictException(
                "A message with this WhatsApp message ID already exists."
            )

    new_message = message_model.Message(
        conversation_id=message_data.conversation_id,
        sender_type=message_data.sender_type,
        staff_id=message_data.staff_id,
        direction=message_data.direction,
        message_type=message_data.message_type,
        content=message_data.content,
        media_urls=message_data.media_urls,
        status=message_data.status,
        whatsapp_message_id=message_data.whatsapp_message_id,
    )

    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)

    response = message_schema.MessageResponse.model_validate(new_message)

    # Broadcast new message to dashboard
    try:
        await websocket_service.broadcast(
            utils.WebSocketEvent.NEW_MESSAGE.value,
            {
                "id": str(response.id),
                "conversation_id": str(response.conversation_id),
                "sender_type": response.sender_type,
                "staff_id": str(response.staff_id) if response.staff_id else None,
                "direction": response.direction,
                "message_type": response.message_type,
                "status": response.status,
                "content": response.content,
                "media_urls": response.media_urls,
                "created_at": response.created_at.isoformat()
                if response.created_at
                else None,
            },
        )
    except Exception:
        pass

    return response


async def get_message_by_id(
    db: AsyncSession, message_id: str
) -> message_schema.MessageResponse:
    result = await db.execute(
        select(message_model.Message).filter(message_model.Message.id == message_id)
    )
    message = result.scalars().first()

    if not message:
        raise exceptions.NotFoundException("Message not found.")

    return message_schema.MessageResponse.model_validate(message)


async def get_all_messages(db: AsyncSession) -> list[message_schema.MessageResponse]:
    result = await db.execute(select(message_model.Message))
    messages = result.scalars().all()
    return [message_schema.MessageResponse.model_validate(m) for m in messages]


async def get_messages_by_conversation_id(
    db: AsyncSession, conversation_id: str
) -> list[message_schema.MessageResponse]:
    result = await db.execute(
        select(message_model.Message)
        .filter(message_model.Message.conversation_id == conversation_id)
        .order_by(message_model.Message.created_at.asc())
    )
    messages = result.scalars().all()
    return [message_schema.MessageResponse.model_validate(m) for m in messages]


async def get_message_by_whatsapp_message_id(
    db: AsyncSession, whatsapp_message_id: str
) -> message_schema.MessageResponse:
    result = await db.execute(
        select(message_model.Message).filter(
            message_model.Message.whatsapp_message_id == whatsapp_message_id
        )
    )
    message = result.scalars().first()

    if not message:
        raise exceptions.NotFoundException("Message not found.")

    return message_schema.MessageResponse.model_validate(message)


async def update_message(
    db: AsyncSession, message_id: str, message_data: message_schema.MessageSchema
) -> message_schema.MessageResponse:
    result = await db.execute(
        select(message_model.Message).filter(message_model.Message.id == message_id)
    )
    message = result.scalars().first()

    if not message:
        raise exceptions.NotFoundException("Message not found.")

    if message_data.whatsapp_message_id:
        dup_result = await db.execute(
            select(message_model.Message).filter(
                message_model.Message.whatsapp_message_id
                == message_data.whatsapp_message_id,
                message_model.Message.id != message_id,
            )
        )
        if dup_result.scalars().first():
            raise exceptions.ConflictException(
                "WhatsApp message ID is already taken by another message."
            )

    message.conversation_id = message_data.conversation_id
    message.sender_type = message_data.sender_type
    message.staff_id = message_data.staff_id
    message.direction = message_data.direction
    message.message_type = message_data.message_type
    message.content = message_data.content
    message.media_urls = message_data.media_urls
    message.status = message_data.status
    message.whatsapp_message_id = message_data.whatsapp_message_id

    await db.commit()
    await db.refresh(message)

    return message_schema.MessageResponse.model_validate(message)


async def update_message_status(
    db: AsyncSession, message_id: str, status: str
) -> message_schema.MessageResponse:
    result = await db.execute(
        select(message_model.Message).filter(message_model.Message.id == message_id)
    )
    message = result.scalars().first()

    if not message:
        raise exceptions.NotFoundException("Message not found.")

    message.status = status
    await db.commit()
    await db.refresh(message)

    return message_schema.MessageResponse.model_validate(message)


async def delete_message(db: AsyncSession, message_id: str):
    result = await db.execute(
        select(message_model.Message).filter(message_model.Message.id == message_id)
    )
    message = result.scalars().first()

    if not message:
        raise exceptions.NotFoundException("Message not found.")

    await db.delete(message)
    await db.commit()
