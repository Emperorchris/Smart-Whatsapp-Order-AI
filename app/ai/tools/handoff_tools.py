from sqlalchemy import select
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...services import human_handoff_service, conversation_service, whatsapp_service, customer_service
from ...db.schemas import human_hand_off_schema
from ...db.model.message_model import Message
from ...db.model.human_hand_off_model import HumanHandOff
from ...core.utils import HandOffStatus, HandOffTriggeredBy, MessageSenderType


@tool
async def request_human_agent(
    config: RunnableConfig, reason: str = "Customer requested a human agent"
) -> str:
    """Transfer the customer to a human agent.
    Use this when:
    - The customer explicitly asks to speak to a human
    - The customer is frustrated or upset
    - You cannot handle their request
    - The issue requires human judgement (refunds, complaints, etc.)"""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]
    conversation_id = config["configurable"]["conversation_id"]

    try:
        handoff_data = human_hand_off_schema.HumanHandOffSchema(
            conversation_id=conversation_id,
            triggered_by=HandOffTriggeredBy.CUSTOMER.value,
            reason=reason,
            assigned_staff_id=None,
            status=HandOffStatus.PENDING.value,
        )

        await human_handoff_service.create_handoff(db, handoff_data)
        await conversation_service.start_handoff(db, conversation_id, reason=reason)

        await whatsapp_service.notify_all_staff(
            db=db,
            message=f"Customer {customer_id} has been transferred to a human agent. Reason: {reason}",
            customer_id=customer_id,
        )

        return "Customer has been connected to a human agent. Staff have been notified."
    except Exception:
        return "You already have a pending request to speak with a human agent. Our team has been notified and will get to you shortly. Please hang tight!"


@tool
async def cancel_handoff_request(
    config: RunnableConfig, reason: str = "Handoff cancelled by customer"
) -> str:
    """Cancel an active handoff request.
    Use this when:
    - The customer changes their mind and wants to continue with the AI
    - The handoff is no longer needed
    - The issue has been resolved while waiting for a human agent"""

    db = config["configurable"]["db"]
    conversation_id = config["configurable"]["conversation_id"]

    # Get the active handoff for this conversation
    handoffs = await human_handoff_service.get_handoffs_by_conversation_id(
        db, conversation_id
    )

    active_handoff = None
    for handoff in handoffs:
        if handoff.status in [
            HandOffStatus.PENDING.value,
            HandOffStatus.ACTIVE.value,
            HandOffStatus.REQUESTED.value,
        ]:
            active_handoff = handoff
            break

    if not active_handoff:
        return "No active handoff request found for this conversation."

    # Cancel the handoff
    await human_handoff_service.cancel_handoff(db, active_handoff.id)
    await conversation_service.resume_ai(
        db, conversation_id, handoff_status=HandOffStatus.CANCELLED
    )

    return "Handoff request has been cancelled. You are now back to the AI assistant."


@tool
async def confirm_resolve_handoff(config: RunnableConfig) -> str:
    """Send confirmation buttons before resolving a handoff.
    Use this FIRST when a staff member wants to close/resolve/end a handoff.
    NEVER call resolve_handoff_request directly — always confirm first."""

    customer_phone = config["configurable"].get("customer_whatsapp_number", "")

    if not customer_phone:
        return "Could not send confirmation. Please confirm: do you want to close this handoff? Reply 'yes' to confirm."

    await whatsapp_service.send_interactive_buttons(
        to=customer_phone,
        body="Are you sure you want to close this handoff session? The customer will be returned to the AI assistant.",
        buttons=[
            {"id": "handoff_resolve_yes", "title": "Yes, close it"},
            {"id": "handoff_resolve_no", "title": "No, keep it"},
        ],
        header="Close Handoff",
    )

    return "Confirmation buttons sent. Waiting for staff to confirm."


@tool
async def resolve_handoff_request(config: RunnableConfig) -> str:
    """Resolve an active handoff request. ONLY call this after staff confirms via the confirmation button.
    Use this when:
    - Staff confirmed they want to close the handoff
    - The customer replied 'handoff_resolve_yes'"""

    db = config["configurable"]["db"]
    conversation_id = config["configurable"]["conversation_id"]

    # Get the active handoff for this conversation
    handoffs = await human_handoff_service.get_handoffs_by_conversation_id(
        db, conversation_id
    )

    active_handoff = None
    for handoff in handoffs:
        if handoff.status in [
            HandOffStatus.PENDING.value,
            HandOffStatus.ACTIVE.value,
            HandOffStatus.REQUESTED.value,
        ]:
            active_handoff = handoff
            break

    if not active_handoff:
        return "No active handoff request found for this conversation."

    # Resolve the handoff
    await human_handoff_service.update_handoff_status(
        db, active_handoff.id, HandOffStatus.RESOLVED
    )
    await conversation_service.resume_ai(
        db, conversation_id, handoff_status=HandOffStatus.RESOLVED
    )

    # Notify the customer that AI is back
    try:
        conv = await conversation_service.get_conversation_by_id(db, str(conversation_id))
        cust = await customer_service.get_customer_by_id(db, str(conv.customer_id))
        await whatsapp_service.send_message(
            to=cust.whatsapp_number,
            body=(
                "Hey! 👋 Our support team is done helping you out. "
                "I'm back and ready to assist you with anything else you need!\n\n"
                "Feel free to browse products, check your orders, or just chat. What's up?"
            ),
        )
    except Exception:
        pass

    return (
        "Handoff closed. The customer has been notified that AI is back."
    )


@tool
async def check_handoff_status(config: RunnableConfig) -> str:
    """Check the current status of an active handoff for this conversation.
    Use this to:
    - Determine if you're currently in a handoff with a human agent
    - Check if a handoff request is still pending
    - Know the current status of the handoff interaction"""

    db = config["configurable"]["db"]
    conversation_id = config["configurable"]["conversation_id"]

    result = await human_handoff_service.check_handoff_status(db, conversation_id)
    
    return result


@tool
async def claim_next_handoff(config: RunnableConfig) -> str:
    """Claim the next pending customer handoff from the queue.
    Use this when a staff member wants to pick up the next waiting customer.
    Only works for staff members."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    try:
        customer = await customer_service.get_customer_by_id(db, customer_id)
    except Exception:
        return "Could not identify you."

    # Find staff by the customer's phone number (staff uses the same flow as customer when no handoff)
    staff = await whatsapp_service.identify_staff_by_phone(db, customer.whatsapp_number)
    if not staff:
        return "This command is only available for staff members."

    try:
        handoff = await human_handoff_service.claim_next_pending_handoff(db, str(staff.id))
        await conversation_service.activate_handoff_for_staff(db, str(handoff.conversation_id), str(staff.id))

        # Get customer details for the handoff
        conv = await conversation_service.get_conversation_by_id(db, str(handoff.conversation_id))
        cust = await customer_service.get_customer_by_id(db, str(conv.customer_id))

        # Fetch the last 20 customer-only messages
        msg_result = await db.execute(
            select(Message).filter(
                Message.conversation_id == str(handoff.conversation_id),
                Message.sender_type == MessageSenderType.CUSTOMER.value,
            ).order_by(Message.created_at.desc()).limit(20)
        )
        recent_messages = list(reversed(msg_result.scalars().all()))

        chat_history = ""
        if recent_messages:
            msg_lines = []
            for msg in recent_messages:
                time_str = msg.created_at.strftime("%d/%m %H:%M") if msg.created_at else ""
                content = msg.content or "[media]"
                msg_lines.append(f"  [{time_str}] {content}")
            chat_history = "\n\n*Recent messages from customer:*\n" + "\n".join(msg_lines)

        return (
            f"You've been assigned a new customer!\n\n"
            f"• Customer: *{cust.display_name or cust.name}*\n"
            f"• WhatsApp: {cust.whatsapp_number}\n"
            f"• Segment: {cust.customer_segment or 'N/A'}\n"
            f"• Reason: {handoff.reason or 'Not specified'}"
            f"{chat_history}\n\n"
            f"Your messages will now be forwarded to this customer. When done, ask me to resolve the handoff."
        )
    except Exception as exc:
        error_msg = str(exc)
        if ": " in error_msg:
            error_msg = error_msg.split(": ", 1)[1]
        return error_msg


@tool
async def get_pending_handoffs(config: RunnableConfig) -> str:
    """View all pending/requested handoffs waiting in the queue.
    Use this when a staff member asks how many customers are waiting or wants to see the queue."""

    db = config["configurable"]["db"]

    from sqlalchemy import select, func
    from ...db.model import human_hand_off_model

    result = await db.execute(
        select(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.status.in_([
                HandOffStatus.PENDING.value,
                HandOffStatus.REQUESTED.value,
            ])
        ).order_by(human_hand_off_model.HumanHandOff.requested_at.asc())
    )
    handoffs = result.scalars().all()

    if not handoffs:
        return "No pending handoffs in the queue right now."

    from ...services import customer_service, conversation_service as conv_svc

    lines = []
    for h in handoffs:
        try:
            conv = await conv_svc.get_conversation_by_id(db, str(h.conversation_id))
            cust = await customer_service.get_customer_by_id(db, str(conv.customer_id))
            name = cust.display_name or cust.name
            phone = cust.whatsapp_number
        except Exception:
            name = "Unknown"
            phone = "N/A"

        lines.append(
            f"• *{name}* ({phone})\n"
            f"  Status: {h.status}\n"
            f"  Reason: {h.reason or 'Not specified'}\n"
            f"  Waiting since: {h.requested_at.strftime('%d-%m-%Y %H:%M') if h.requested_at else 'N/A'}"
        )

    return f"*{len(handoffs)}* customer(s) waiting:\n\n" + "\n\n".join(lines)


handoff_tools = [
    request_human_agent,
    cancel_handoff_request,
    confirm_resolve_handoff,
    resolve_handoff_request,
    check_handoff_status,
    claim_next_handoff,
    get_pending_handoffs,
]
