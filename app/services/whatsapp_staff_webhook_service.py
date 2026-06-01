import time

from loguru import logger
from sqlalchemy import select, func, String
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

from ..core import utils, exceptions
from ..db.model import human_hand_off_model, staff_model
from ..db.model.message_model import Message
from ..db.schemas.message_schema import MessageSchema
from ..ai.memory.conversation_memory import (
    load_conversation_history,
    save_agent_messages,
    _extract_text_content,
)
from . import (
    conversation_service,
    customer_service,
    human_handoff_service,
    message_service,
    whatsapp_service,
)

# ── Staff chat mode tracking (in-memory) ──
# Tracks whether each staff member is talking to AI or to the customer
_staff_chat_mode: dict[str, str] = {}  # staff_id → "ai" | "customer"
_staff_last_message_time: dict[str, float] = {}  # staff_id → timestamp

_MODE_REMINDER_GAP_SECONDS = 30


def _get_staff_mode(staff_id: str) -> str:
    return _staff_chat_mode.get(str(staff_id), utils.StaffChatMode.AI.value)


def set_staff_mode(staff_id: str, mode: str) -> None:
    _staff_chat_mode[str(staff_id)] = mode
    _staff_last_message_time[str(staff_id)] = time.time()


def clear_staff_mode(staff_id: str) -> None:
    _staff_chat_mode.pop(str(staff_id), None)
    _staff_last_message_time.pop(str(staff_id), None)


def _should_send_reminder(staff_id: str) -> bool:
    last = _staff_last_message_time.get(str(staff_id))
    if last is None:
        return True
    return (time.time() - last) >= _MODE_REMINDER_GAP_SECONDS


async def _send_mode_switch_button(staff_number: str, current_mode: str) -> None:
    """Send mode switch + quick action buttons based on current mode."""
    if current_mode == utils.StaffChatMode.CUSTOMER.value:
        await whatsapp_service.send_interactive_buttons(
            to=staff_number,
            body="You're chatting with the customer. Tap the button below to switch to AI mode and talk to me instead.",
            buttons=[
                {"id": "staff_mode_ai", "title": "Talk to AI"},
                {"id": "staff_cmd_done", "title": "Done"},
                {"id": "staff_cmd_skip", "title": "Skip"},
            ],
        )
    else:
        await whatsapp_service.send_interactive_buttons(
            to=staff_number,
            body="You're in AI mode. Tap the button below to switch to customer mode and talk to the customer instead.",
            buttons=[
                {"id": "staff_mode_customer", "title": "Talk to Customer"},
                {"id": "staff_cmd_done", "title": "Done"},
                {"id": "staff_cmd_info", "title": "Info"},
            ],
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


async def get_staff_by_phone(db: AsyncSession, phone: str):
    """Find staff by phone number using all format variants."""
    variants = _phone_variants(phone)
    result = await db.execute(
        select(staff_model.Staff).filter(
            staff_model.Staff.whatsapp_number.in_(variants)
        )
    )
    return result.scalars().first()


async def handle_staff_incoming_message(
    db: AsyncSession,
    staff_number: str,
    body: str,
    message_sid: str,
    interactive_id: str | None = None,
):
    """Route staff messages using mode switching:
    - During active handoff: mode determines routing (AI mode vs Customer mode)
    - Interactive buttons toggle mode
    - # prefix always routes to AI (backward compatible)
    - No active handoff: all messages → AI assistant
    """
    logger.info(
        "staff_webhook: received message from {} — body={!r}, interactive_id={!r}",
        staff_number,
        body[:100],
        interactive_id,
    )
    clean_body = body.strip()

    staff = await get_staff_by_phone(db, staff_number)
    if not staff:
        logger.warning(
            "staff_webhook: identified as staff but not found in DB: {}", staff_number
        )
        return None

    staff_id = str(staff.id)

    # Handle claim buttons (work regardless of active handoff state)
    if interactive_id and (
        interactive_id.startswith("claim_cust_")
        or interactive_id.startswith("claim_ai_")
    ):
        await _handle_claim_button(db, staff, staff_number, interactive_id)
        return "handled"

    # Check if staff has an active handoff
    handoff_result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
            human_hand_off_model.HumanHandOff.status
            == utils.HandOffStatus.ACTIVE.value,
        )
    )
    active_handoff = handoff_result.scalars().first()

    if active_handoff:
        # 1. Handle mode switch buttons
        if interactive_id == "staff_mode_customer":
            logger.info("staff_webhook: staff switching to CUSTOMER mode")
            set_staff_mode(staff_id, utils.StaffChatMode.CUSTOMER.value)
            await whatsapp_service.send_message(
                to=staff_number,
                body="Switched to *Customer Mode*. Your messages will now be sent directly to the customer.",
            )
            return "handled"

        if interactive_id == "staff_mode_ai":
            logger.info("staff_webhook: staff switching to AI mode")
            set_staff_mode(staff_id, utils.StaffChatMode.AI.value)
            await whatsapp_service.send_message(
                to=staff_number,
                body="Switched to *AI Mode*. You're now talking to me.",
            )
            await _send_mode_switch_button(staff_number, utils.StaffChatMode.AI.value)
            return "handled"

        # 2. Quick action buttons — handle Done/Skip directly, route Info to AI
        if interactive_id == "staff_cmd_done":
            logger.info("staff_webhook: Done button pressed, resolving handoff")
            clear_staff_mode(staff_id)
            await conversation_service.resume_ai(
                db, str(active_handoff.conversation_id)
            )
            try:
                conv = await conversation_service.get_conversation_by_id(
                    db, str(active_handoff.conversation_id)
                )
                cust = await customer_service.get_customer_by_id(
                    db, str(conv.customer_id)
                )
                await whatsapp_service.send_message(
                    to=cust.whatsapp_number,
                    body="Hey! 👋 Our support team is done helping you out. I'm back and ready to assist you with anything else you need!",
                )
            except Exception:
                pass
            await whatsapp_service.send_message(
                to=staff_number, body="Handoff resolved. Customer returned to AI."
            )
            return "handled"

        if interactive_id == "staff_cmd_skip":
            logger.info(
                "staff_webhook: Skip button pressed, returning handoff to queue"
            )
            clear_staff_mode(staff_id)
            active_handoff.assigned_staff_id = None
            active_handoff.status = utils.HandOffStatus.PENDING.value
            active_handoff.claimed_at = None
            await db.commit()
            await whatsapp_service.send_message(
                to=staff_number, body="Handoff returned to the queue."
            )
            return "handled"

        if interactive_id == "staff_cmd_info":
            logger.info("staff_webhook: Info button pressed, routing to AI")
            await _process_staff_ai_message(
                db,
                staff,
                utils.StaffConversationCommand.INFO.value,
                active_handoff=active_handoff,
            )
            return "handled"

        # 3. Handoff resolve buttons always go to AI
        if interactive_id and interactive_id.startswith("handoff_"):
            logger.info("staff_webhook: handoff interactive button, routing to AI")
            await _process_staff_ai_message(
                db, staff, clean_body, active_handoff=active_handoff
            )
            return "handled"

        # 3. # prefix always routes to AI (backward compatible)
        if clean_body.startswith("#"):
            logger.info("staff_webhook: # command, routing to AI")
            await _process_staff_ai_message(
                db, staff, clean_body, active_handoff=active_handoff
            )
            return "handled"

        # 4. Route based on current mode
        # If mode is not in memory (e.g. server restarted after claim), default to
        # CUSTOMER mode — staff claimed the handoff to talk to the customer.
        current_mode = _staff_chat_mode.get(str(staff_id))
        if current_mode is None:
            logger.info(
                "staff_webhook: mode not in memory (server restart?), defaulting to CUSTOMER mode"
            )
            current_mode = utils.StaffChatMode.CUSTOMER.value
            set_staff_mode(staff_id, current_mode)

        if current_mode == utils.StaffChatMode.CUSTOMER.value:
            logger.info("staff_webhook: CUSTOMER mode, forwarding to customer")
            await _handle_staff_reply(db, staff_number, clean_body, message_sid)

            # Send reminder button after a gap
            if _should_send_reminder(staff_id):
                await _send_mode_switch_button(
                    staff_number, utils.StaffChatMode.CUSTOMER.value
                )
            _staff_last_message_time[staff_id] = time.time()

            return "handled"
        else:
            logger.info("staff_webhook: AI mode, routing to AI")
            await _process_staff_ai_message(
                db, staff, clean_body, active_handoff=active_handoff
            )
            return "handled"

    # No active handoff — route to AI
    logger.info("staff_webhook: no active handoff, routing to AI assistant")
    await _process_staff_ai_message(db, staff, clean_body, active_handoff=None)
    return "handled"


async def _handle_claim_button(
    db: AsyncSession, staff, staff_number: str, interactive_id: str
) -> None:
    """Handle claim_cust_* and claim_ai_* button taps from pending handoff cards."""
    staff_id = str(staff.id)

    # Parse mode and handoff short ID from button ID
    if interactive_id.startswith("claim_cust_"):
        target_mode = utils.StaffChatMode.CUSTOMER.value
        handoff_short_id = interactive_id[len("claim_cust_") :]
    else:
        target_mode = utils.StaffChatMode.AI.value
        handoff_short_id = interactive_id[len("claim_ai_") :]

    # Find the handoff by short ID prefix
    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.status.in_(
                [
                    utils.HandOffStatus.PENDING.value,
                    utils.HandOffStatus.REQUESTED.value,
                ]
            ),
            human_hand_off_model.HumanHandOff.id.cast(String).startswith(
                handoff_short_id
            ),
        )
    )
    handoff = result.scalars().first()

    if not handoff:
        await whatsapp_service.send_message(
            to=staff_number,
            body="This handoff is no longer available. It may have been claimed or cancelled.",
        )
        return

    # Claim the handoff
    try:
        await human_handoff_service.assign_handoff_to_staff(
            db, str(handoff.id), staff_id
        )
        await conversation_service.activate_handoff_for_staff(
            db, str(handoff.conversation_id), staff_id
        )
    except Exception as exc:
        error_msg = str(exc)
        if ": " in error_msg:
            error_msg = error_msg.split(": ", 1)[1]
        await whatsapp_service.send_message(to=staff_number, body=error_msg)
        return

    # Set mode
    set_staff_mode(staff_id, target_mode)

    # Get customer info for confirmation
    try:
        conv = await conversation_service.get_conversation_by_id(
            db, str(handoff.conversation_id)
        )
        cust = await customer_service.get_customer_by_id(db, str(conv.customer_id))
        cust_name = cust.display_name or cust.name
    except Exception:
        cust_name = "the customer"

    mode_label = (
        "Customer" if target_mode == utils.StaffChatMode.CUSTOMER.value else "AI"
    )

    # Fetch last 15 customer messages for context
    msg_result = await db.execute(
        select(Message)
        .filter(
            Message.conversation_id == str(handoff.conversation_id),
            Message.sender_type == utils.MessageSenderType.CUSTOMER.value,
            Message.direction == utils.MessageDirection.INBOUND.value,
        )
        .order_by(Message.created_at.desc())
        .limit(15)
    )
    recent_messages = list(reversed(msg_result.scalars().all()))

    chat_history = ""
    if recent_messages:
        msg_lines = []
        for msg in recent_messages:
            time_str = (
                msg.created_at.strftime("%b %d, %I:%M %p") if msg.created_at else ""
            )
            content = msg.content or "[media]"
            # Skip system-injected messages and truncate long ones
            if content.startswith("[Customer selected") or content.startswith(
                "[Customer wants"
            ):
                continue
            if len(content) > 150:
                content = content[:147] + "..."
            msg_lines.append(f"• {content}\n  _{time_str}_")
        chat_history = "\n\n".join(msg_lines)

    claimed_body = f"Claimed! You're now in *{mode_label} Mode* for *{cust_name}*."
    if chat_history:
        claimed_body += f"\n\n*Customer's recent messages:*\n\n{chat_history}"
    else:
        claimed_body += "\n\nNo recent messages from this customer."

    # WhatsApp text message limit is 4096 chars
    if len(claimed_body) > 4000:
        claimed_body = claimed_body[:3997] + "..."

    await whatsapp_service.send_message(to=staff_number, body=claimed_body)
    await _send_mode_switch_button(staff_number, target_mode)


async def _process_staff_ai_message(
    db: AsyncSession, staff, body: str, active_handoff=None
):
    """Process a staff message through the AI agent and send the reply back to staff."""
    from ..ai.graph import agent_graph

    # Determine conversation context from active handoff (if any)
    conversation_id = None
    customer_id = None
    if active_handoff:
        conversation_id = str(active_handoff.conversation_id)
        try:
            conv = await conversation_service.get_conversation_by_id(
                db, conversation_id
            )
            customer_id = str(conv.customer_id)
        except Exception:
            pass

    # Load conversation history if we have a conversation context
    history = []
    if conversation_id:
        history = await load_conversation_history(db, conversation_id)

    # Append the staff's current message
    history.append(HumanMessage(content=body))

    initial_state = {
        "messages": history,
        "customer_whatsapp_number": staff.whatsapp_number,
        "customer_name": staff.name,
        "customer_display_name": staff.name,
        "customer_id": customer_id,
        "conversation_id": conversation_id,
        "sender_type": utils.MessageSenderType.STAFF.value,
        "staff_id": str(staff.id),
    }

    history_count = len(initial_state["messages"])

    try:
        result = await agent_graph.run_agent(
            initial_state,
            db=db,
            customer_id=customer_id,
            conversation_id=conversation_id,
            staff_id=str(staff.id),
        )

        raw_content = result["messages"][-1].content if result["messages"] else None
        ai_reply = (
            _extract_text_content(raw_content)
            if raw_content
            else "Sorry, I couldn't process that right now."
        )

        # Save new messages to conversation history (only if we have a conversation)
        if conversation_id:
            new_messages = result["messages"][history_count:]
            await save_agent_messages(db, conversation_id, new_messages)

        # Send the reply to staff via WhatsApp
        await whatsapp_service.send_message(to=staff.whatsapp_number, body=ai_reply)

    except Exception as exc:
        logger.error(
            "staff_webhook: AI processing failed for staff {} — {}", staff.id, exc
        )
        await whatsapp_service.send_message(
            to=staff.whatsapp_number,
            body="Something went wrong on my end. Please try again.",
        )


async def _handle_staff_reply(
    db: AsyncSession, staff_number: str, body: str, message_sid: str
) -> None:
    staff = await get_staff_by_phone(db, staff_number)

    if not staff:
        logger.warning(
            "staff_webhook: no staff found for number {} in _handle_staff_reply",
            staff_number,
        )
        return

    handoff_result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
            human_hand_off_model.HumanHandOff.status
            == utils.HandOffStatus.ACTIVE.value,
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
        db, str(conversation.customer_id)
    )

    sent = await whatsapp_service.send_message(to=customer.whatsapp_number, body=body)

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


async def _handle_staff_command(
    db: AsyncSession, staff_number: str, command: str
) -> None:
    staff = await get_staff_by_phone(db, staff_number)

    if not staff:
        logger.warning(
            "staff_webhook: no staff found for number {} in _handle_staff_command",
            staff_number,
        )
        return

    if command == utils.StaffConversationCommand.DONE.value:
        handoff_result = await db.execute(
            select(human_hand_off_model.HumanHandOff).filter(
                human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
                human_hand_off_model.HumanHandOff.status
                == utils.HandOffStatus.ACTIVE.value,
            )
        )
        active_handoff = handoff_result.scalars().first()

        if active_handoff:
            clear_staff_mode(str(staff.id))
            await conversation_service.resume_ai(
                db, str(active_handoff.conversation_id)
            )
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
                db, str(staff.id)
            )
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
            select(func.count())
            .select_from(human_hand_off_model.HumanHandOff)
            .filter(
                human_hand_off_model.HumanHandOff.status.in_(
                    [
                        utils.HandOffStatus.REQUESTED.value,
                        utils.HandOffStatus.PENDING.value,
                    ]
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
                human_hand_off_model.HumanHandOff.status
                == utils.HandOffStatus.ACTIVE.value,
            )
        )
        active_handoff = handoff_result.scalars().first()

        if active_handoff:
            clear_staff_mode(str(staff.id))
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
                human_hand_off_model.HumanHandOff.status
                == utils.HandOffStatus.ACTIVE.value,
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
