from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import utils, exceptions
from ..db.model import human_hand_off_model, staff_model
from ..db.schemas.message_schema import MessageSchema
from . import (
    conversation_service,
    customer_service,
    human_handoff_service,
    message_service,
    whatsapp_service,
)


def _phone_variants(phone: str) -> set[str]:
    """Build all possible Nigerian phone formats for matching."""
    p = phone.strip().lstrip("+")
    variants = {p, "+" + p}
    if p.startswith("234") and len(p) > 10:
        local = p[3:]
        variants.update({local, "0" + local, "+234" + local})
    elif p.startswith("0") and len(p) >= 10:
        without_zero = p[1:]
        variants.update({without_zero, "234" + without_zero, "+234" + without_zero})
    elif len(p) >= 9:
        variants.update({"0" + p, "234" + p, "+234" + p})
    return variants


async def _get_staff_by_phone(db: AsyncSession, phone: str):
    """Find staff by phone number using all format variants."""
    variants = _phone_variants(phone)
    result = await db.execute(
        select(staff_model.Staff).filter(
            staff_model.Staff.whatsapp_number.in_(variants)
        )
    )
    return result.scalars().first()


async def handle_staff_incoming_message(db: AsyncSession, staff_number: str, body: str, message_sid: str, interactive_id: str | None = None):
    """Route staff messages:
    - During active handoff: # prefix or interactive button replies → AI, everything else → forward to customer
    - No active handoff: all messages → AI assistant
    """
    logger.info("staff_webhook: received message from {} — body={!r}, interactive_id={!r}", staff_number, body[:100], interactive_id)
    clean_body = body.strip()

    # Check if staff has an active handoff
    staff = await _get_staff_by_phone(db, staff_number)
    if staff:
        handoff_result = await db.execute(
            select(human_hand_off_model.HumanHandOff).filter(
                human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
                human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
            )
        )
        active_handoff = handoff_result.scalars().first()

        if active_handoff:
            # During active handoff: # commands and interactive button replies go to AI
            is_ai_message = clean_body.startswith("#") or (interactive_id and interactive_id.startswith("handoff_"))

            if is_ai_message:
                logger.info("staff_webhook: staff has active handoff but sent AI command, routing to AI")
                return None
            else:
                logger.info("staff_webhook: staff has active handoff, forwarding to customer")
                await _handle_staff_reply(db, staff_number, clean_body, message_sid)
                return "handled"

    # No active handoff — route to AI
    logger.info("staff_webhook: no active handoff, routing to AI assistant")
    return None


async def _handle_staff_reply(db: AsyncSession, staff_number: str, body: str, message_sid: str) -> None:
    staff = await _get_staff_by_phone(db, staff_number)

    if not staff:
        logger.warning("staff_webhook: no staff found for number {} in _handle_staff_reply", staff_number)
        return

    handoff_result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
        )
    )
    active_handoff = handoff_result.scalars().first()

    if not active_handoff:
        await whatsapp_service.send_message(
            to=staff_number,
            body="You have no active handoff. Your message was not delivered.",
        )
        return

    conversation = await conversation_service.get_conversation_by_id(
        db, str(active_handoff.conversation_id)
    )
    customer = await customer_service.get_customer_by_id(
        db, str(conversation.customer_id))

    sent = await whatsapp_service.send_message(
        to=customer.whatsapp_number, body=body)

    await message_service.create_message(
        db,
        MessageSchema(
            conversation_id=active_handoff.conversation_id,
            sender_type=utils.MessageSenderType.STAFF.value,
            staff_id=staff.id,
            direction=utils.MessageDirection.OUTBOUND.value,
            message_type=utils.MessageType.TEXT.value,
            content=body,
            status=utils.MessageStatus.SENT.value,
            whatsapp_message_id=sent.get("message_id") or sent.get("sid"),
        ),
    )

    await message_service.create_message(
        db,
        MessageSchema(
            conversation_id=active_handoff.conversation_id,
            sender_type=utils.MessageSenderType.STAFF.value,
            staff_id=staff.id,
            direction=utils.MessageDirection.INBOUND.value,
            message_type=utils.MessageType.TEXT.value,
            content=body,
            status=utils.MessageStatus.DELIVERED.value,
            whatsapp_message_id=message_sid,
        ),
    )


async def _handle_staff_command(db: AsyncSession, staff_number: str, command: str) -> None:
    staff = await _get_staff_by_phone(db, staff_number)

    if not staff:
        logger.warning("staff_webhook: no staff found for number {} in _handle_staff_command", staff_number)
        return

    if command == utils.StaffConversationCommand.DONE.value:
        handoff_result = await db.execute(
            select(human_hand_off_model.HumanHandOff).filter(
                human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
                human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
            )
        )
        active_handoff = handoff_result.scalars().first()

        if active_handoff:
            await conversation_service.resume_ai(
                db, str(active_handoff.conversation_id))
            await whatsapp_service.send_message(
                to=staff_number,
                body="✅ Handoff resolved. AI has resumed for this conversation.",
            )
        else:
            await whatsapp_service.send_message(
                to=staff_number,
                body="You have no active handoff to resolve.",
            )

    elif command == utils.StaffConversationCommand.NEXT.value:
        try:
            handoff = await human_handoff_service.claim_next_pending_handoff(
                db, str(staff.id))
            await conversation_service.activate_handoff_for_staff(
                db, str(handoff.conversation_id), str(staff.id)
            )
            await whatsapp_service.send_message(
                to=staff_number,
                body=(
                    f"📩 You've been assigned a new customer.\n"
                    f"Conversation ID: {handoff.conversation_id}\n"
                    f"Reason: {handoff.reason or 'Not specified'}"
                ),
            )
        except exceptions.ConflictException:
            await whatsapp_service.send_message(
                to=staff_number,
                body=f"You already have an active handoff. Use *{utils.StaffConversationCommand.DONE.value}* to resolve it or *{utils.StaffConversationCommand.SKIP.value}* to skip before claiming another.",
            )
        except exceptions.NotFoundException:
            await whatsapp_service.send_message(
                to=staff_number,
                body="No pending handoffs in the queue right now.",
            )
        except Exception as exc:
            logger.error("staff_webhook: #next failed — {}", exc)
            await whatsapp_service.send_message(
                to=staff_number,
                body="Something went wrong. Please try again.",
            )

    elif command == utils.StaffConversationCommand.QUEUE.value:
        count_result = await db.execute(
            select(func.count()).select_from(human_hand_off_model.HumanHandOff).filter(
                human_hand_off_model.HumanHandOff.status.in_(
                    [utils.HandOffStatus.REQUESTED.value,
                        utils.HandOffStatus.PENDING.value]
                )
            )
        )
        pending = count_result.scalar()
        await whatsapp_service.send_message(
            to=staff_number,
            body=f"📋 There are *{pending}* customer(s) waiting in the queue.",
        )

    elif command == utils.StaffConversationCommand.SKIP.value:
        handoff_result = await db.execute(
            select(human_hand_off_model.HumanHandOff).filter(
                human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
                human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
            )
        )
        active_handoff = handoff_result.scalars().first()

        if active_handoff:
            active_handoff.assigned_staff_id = None
            active_handoff.status = utils.HandOffStatus.PENDING.value
            active_handoff.claimed_at = None
            await db.commit()
            await whatsapp_service.send_message(
                to=staff_number,
                body="↩️ Handoff returned to the queue. Another agent can pick it up.",
            )
        else:
            await whatsapp_service.send_message(
                to=staff_number,
                body="You have no active handoff to skip.",
            )

    elif command == utils.StaffConversationCommand.INFO.value:
        handoff_result = await db.execute(
            select(human_hand_off_model.HumanHandOff).filter(
                human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
                human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
            )
        )
        active_handoff = handoff_result.scalars().first()

        if active_handoff:
            await whatsapp_service.send_message(
                to=staff_number,
                body=(
                    "ℹ️ *Active Handoff Info*\n"
                    f"Conversation ID: {active_handoff.conversation_id}\n"
                    f"Reason: {active_handoff.reason or 'Not specified'}\n"
                    f"Status: {active_handoff.status} \n"
                    f"Triggered by: {active_handoff.triggered_by}\n"
                    f"Requested at: {active_handoff.requested_at.strftime('%d-%m-%Y %H:%M')}"
                ),
            )
        else:
            await whatsapp_service.send_message(
                to=staff_number,
                body="You have no active handoff at the moment.",
            )

    else:
        await whatsapp_service.send_message(
            to=staff_number,
            body=(
                "Available commands:\n"
                f"{utils.StaffConversationCommand.NEXT.value} — claim the next customer\n"
                f"{utils.StaffConversationCommand.DONE.value} — resolve your current handoff\n"
                f"{utils.StaffConversationCommand.SKIP.value} — return handoff to queue\n"
                f"{utils.StaffConversationCommand.QUEUE.value} — see how many customers are waiting\n"
                f"{utils.StaffConversationCommand.INFO.value} — view your current handoff details"
            ),
        )
