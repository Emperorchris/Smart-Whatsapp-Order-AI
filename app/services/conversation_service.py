import math
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import conversation_schema
from ..core import exceptions, utils
from ..db.model import conversation_model, staff_model, human_hand_off_model
from ..db.model.customer_model import Customer


async def create_conversation(db: AsyncSession, conversation_data: conversation_schema.ConversationSchema) -> conversation_schema.ConversationResponse:
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
    await db.commit()
    await db.refresh(new_conversation)

    return conversation_schema.ConversationResponse.model_validate(new_conversation)


async def get_conversation_by_id(db: AsyncSession, conversation_id: str) -> conversation_schema.ConversationResponse:
    result = await db.execute(
        select(conversation_model.Conversation).filter(
            conversation_model.Conversation.id == conversation_id
        )
    )
    conversation = result.scalars().first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")

    return conversation_schema.ConversationResponse.model_validate(conversation)


async def get_all_conversations(db: AsyncSession) -> list[conversation_schema.ConversationResponse]:
    result = await db.execute(select(conversation_model.Conversation))
    conversations = result.scalars().all()
    return [conversation_schema.ConversationResponse.model_validate(c) for c in conversations]


async def get_conversations_by_customer_id(db: AsyncSession, customer_id: str) -> list[conversation_schema.ConversationResponse]:
    result = await db.execute(
        select(conversation_model.Conversation).filter(
            conversation_model.Conversation.customer_id == customer_id
        )
    )
    conversations = result.scalars().all()
    return [conversation_schema.ConversationResponse.model_validate(c) for c in conversations]


async def start_handoff(db: AsyncSession, conversation_id: str, reason: str = None) -> conversation_schema.ConversationResponse:
    result = await db.execute(
        select(conversation_model.Conversation).filter(
            conversation_model.Conversation.id == conversation_id
        )
    )
    conversation = result.scalars().first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")

    if conversation.handoff_to_human and conversation.handoff_status == utils.HandOffStatus.ACTIVE.value:
        raise exceptions.ConflictException("Handoff is already in progress for this conversation.")

    conversation.handoff_to_human = True
    conversation.ai_enabled = False
    conversation.assigned_staff_id = None
    conversation.handoff_status = utils.HandOffStatus.PENDING.value
    conversation.handoff_started_at = datetime.now(tz=timezone.utc).replace(tzinfo=None) if not conversation.handoff_started_at else conversation.handoff_started_at
    conversation.handoff_ended_at = None
    conversation.handoff_reason = reason

    await db.commit()
    await db.refresh(conversation)

    return conversation_schema.ConversationResponse.model_validate(conversation)


async def activate_handoff_for_staff(db: AsyncSession, conversation_id: str, staff_id: str) -> conversation_schema.ConversationResponse:
    result = await db.execute(
        select(conversation_model.Conversation).filter(
            conversation_model.Conversation.id == conversation_id
        )
    )
    conversation = result.scalars().first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")

    staff_result = await db.execute(
        select(staff_model.Staff).filter(staff_model.Staff.id == staff_id)
    )
    staff = staff_result.scalars().first()
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")

    conversation.handoff_to_human = True
    conversation.ai_enabled = False
    conversation.assigned_staff_id = staff.id
    conversation.handoff_status = utils.HandOffStatus.ACTIVE.value
    conversation.handoff_ended_at = None

    await db.commit()
    await db.refresh(conversation)

    return conversation_schema.ConversationResponse.model_validate(conversation)


async def resume_ai(db: AsyncSession, conversation_id: str, handoff_status: utils.HandOffStatus | None = None) -> conversation_schema.ConversationResponse:
    result = await db.execute(
        select(conversation_model.Conversation).filter(
            conversation_model.Conversation.id == conversation_id
        )
    )
    conversation = result.scalars().first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")

    conversation.handoff_to_human = False
    conversation.ai_enabled = True
    conversation.assigned_staff_id = None
    conversation.handoff_status = handoff_status.value if handoff_status else utils.HandOffStatus.RESOLVED.value
    conversation.handoff_ended_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
    conversation.handoff_reason = None

    handoff_result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.conversation_id == conversation_id,
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
        )
    )
    active_handoff = handoff_result.scalars().first()
    if active_handoff:
        active_handoff.status = utils.HandOffStatus.RESOLVED.value
        active_handoff.resolved_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(conversation)

    return conversation_schema.ConversationResponse.model_validate(conversation)


async def update_conversation(db: AsyncSession, conversation_id: str, conversation_data: conversation_schema.ConversationSchema) -> conversation_schema.ConversationResponse:
    result = await db.execute(
        select(conversation_model.Conversation).filter(
            conversation_model.Conversation.id == conversation_id
        )
    )
    conversation = result.scalars().first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")

    conversation.customer_id = conversation_data.customer_id
    conversation.conversation_type = conversation_data.conversation_type
    conversation.status = conversation_data.status

    await db.commit()
    await db.refresh(conversation)

    return conversation_schema.ConversationResponse.model_validate(conversation)


async def delete_conversation(db: AsyncSession, conversation_id: str):
    result = await db.execute(
        select(conversation_model.Conversation).filter(
            conversation_model.Conversation.id == conversation_id
        )
    )
    conversation = result.scalars().first()

    if not conversation:
        raise exceptions.NotFoundException("Conversation not found.")

    await db.delete(conversation)
    await db.commit()


async def get_filtered_conversations(
    db: AsyncSession,
    status: str | None = None,
    handoff_status: str | None = None,
    customer_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> conversation_schema.PaginatedConversationResponse:
    Convo = conversation_model.Conversation

    base = select(
        Convo.id,
        Convo.customer_id,
        Customer.name.label("customer_name"),
        Customer.whatsapp_number.label("customer_whatsapp_number"),
        Convo.status,
        Convo.handoff_status,
        Convo.ai_enabled,
        Convo.started_at,
        Convo.ended_at,
    ).join(Customer, Convo.customer_id == Customer.id)

    count_q = select(func.count(Convo.id)).join(Customer, Convo.customer_id == Customer.id)

    if status:
        base = base.where(Convo.status == status)
        count_q = count_q.where(Convo.status == status)
    if handoff_status:
        base = base.where(Convo.handoff_status == handoff_status)
        count_q = count_q.where(Convo.handoff_status == handoff_status)
    if customer_id:
        base = base.where(Convo.customer_id == customer_id)
        count_q = count_q.where(Convo.customer_id == customer_id)
    if start_date:
        dt = datetime.combine(start_date, datetime.min.time())
        base = base.where(Convo.started_at >= dt)
        count_q = count_q.where(Convo.started_at >= dt)
    if end_date:
        dt = datetime.combine(end_date, datetime.max.time())
        base = base.where(Convo.started_at <= dt)
        count_q = count_q.where(Convo.started_at <= dt)

    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(
        base.order_by(Convo.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).all()

    items = [
        conversation_schema.ConversationListItem(
            id=r.id,
            customer_id=r.customer_id,
            customer_name=r.customer_name,
            customer_whatsapp_number=r.customer_whatsapp_number,
            status=r.status,
            handoff_status=r.handoff_status,
            ai_enabled=r.ai_enabled,
            started_at=r.started_at,
            ended_at=r.ended_at,
        )
        for r in rows
    ]

    return conversation_schema.PaginatedConversationResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if page_size > 0 else 0,
    )
