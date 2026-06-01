from sqlalchemy import select
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...services import human_handoff_service, conversation_service, whatsapp_service, customer_service, staff_service
from ...db.schemas import human_hand_off_schema
from ...db.model.message_model import Message
from ...db.model import human_hand_off_model
from ...core.utils import HandOffStatus, HandOffTriggeredBy, MessageSenderType, StaffChatMode
from ...services.whatsapp_staff_webhook_service import set_staff_mode, clear_staff_mode, _get_staff_mode


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

        handoff = await human_handoff_service.create_handoff(db, handoff_data)
        await conversation_service.start_handoff(db, conversation_id, reason=reason)

        await whatsapp_service.notify_all_staff(
            db=db,
            message=f"A customer needs help.\nReason: {reason}",
            customer_id=customer_id,
            handoff_id=str(handoff.id),
        )

        return "I've notified our team. Please wait a moment while we connect you to a human agent."
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

    # Cancel the handoff and clear staff mode
    staff_id = config["configurable"].get("staff_id")
    if staff_id:
        clear_staff_mode(staff_id)

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

    db = config["configurable"]["db"]
    staff_id = config["configurable"].get("staff_id")

    # Get the staff member's actual phone number
    staff_phone = ""
    try:
        if staff_id:
            staff = await staff_service.get_staff_by_id(db, staff_id)
            staff_phone = staff.whatsapp_number
        else:
            customer_id = config["configurable"]["customer_id"]
            cust_record = await customer_service.get_customer_by_id(db, customer_id)
            staff = await whatsapp_service.identify_staff_by_phone(db, cust_record.whatsapp_number)
            staff_phone = staff.whatsapp_number if staff else cust_record.whatsapp_number
    except Exception:
        staff_phone = config["configurable"].get("customer_whatsapp_number", "")

    if not staff_phone:
        return "Could not send confirmation. Do you want to close this handoff? Reply '#yes' to confirm or '#no' to cancel."

    try:
        await whatsapp_service.send_interactive_buttons(
            to=staff_phone,
            body="Are you sure you want to close this handoff session? The customer will be returned to the AI assistant.",
            buttons=[
                {"id": "handoff_resolve_yes", "title": "Yes, close it"},
                {"id": "handoff_resolve_no", "title": "No, keep it"},
            ],
            header="Close Handoff",
        )
        return "Confirmation buttons sent. Tap the button to confirm."
    except Exception as exc:
        from loguru import logger
        logger.error("confirm_resolve_handoff: failed to send buttons — {}", exc)
        return "I couldn't send the confirmation buttons. Reply '#yes' to close the handoff or '#no' to keep it."


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

    # Resolve the handoff and clear staff mode
    staff_id = config["configurable"].get("staff_id")
    if staff_id:
        clear_staff_mode(staff_id)

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
    staff_id_from_config = config["configurable"].get("staff_id")

    from loguru import logger as _logger

    # Resolve staff member — prefer staff_id from config, fall back to customer phone lookup
    staff = None
    if staff_id_from_config:
        try:
            staff = await staff_service.get_staff_by_id(db, staff_id_from_config)
        except Exception:
            return "Could not identify you as a staff member."
    else:
        customer_id = config["configurable"].get("customer_id")
        try:
            customer = await customer_service.get_customer_by_id(db, customer_id)
            staff = await whatsapp_service.identify_staff_by_phone(db, customer.whatsapp_number)
        except Exception:
            return "Could not identify you."

    if not staff:
        return "This command is only available for staff members."

    _logger.info("claim_next_handoff: staff_id={}, attempting to claim", staff.id)

    try:
        handoff = await human_handoff_service.claim_next_pending_handoff(db, str(staff.id))
        _logger.info("claim_next_handoff: claimed handoff_id={}, conversation_id={}", handoff.id, handoff.conversation_id)
        await conversation_service.activate_handoff_for_staff(db, str(handoff.conversation_id), str(staff.id))

        # Set staff to AI mode and send [Talk to Customer] button
        set_staff_mode(str(staff.id), StaffChatMode.AI.value)

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

        # Send [Talk to Customer] button to staff
        try:
            await whatsapp_service.send_interactive_buttons(
                to=staff.whatsapp_number,
                body="You're in AI mode. Tap below when you're ready to talk to the customer.",
                buttons=[{"id": "staff_mode_customer", "title": "Talk to Customer"}],
            )
        except Exception:
            pass

        return (
            f"You've been assigned a new customer!\n\n"
            f"• Customer: *{cust.display_name or cust.name}*\n"
            f"• WhatsApp: {cust.whatsapp_number}\n"
            f"• Reason: {handoff.reason or 'Not specified'}"
            f"{chat_history}\n\n"
            f"You're in *AI Mode*. Review the customer's details, then tap *Talk to Customer* when ready."
        )
    except Exception as exc:
        _logger.error("claim_next_handoff: FAILED — {}", exc)
        error_msg = str(exc)
        if ": " in error_msg:
            error_msg = error_msg.split(": ", 1)[1]
        return error_msg


@tool
async def get_pending_handoffs(config: RunnableConfig) -> str:
    """View all pending/requested handoffs waiting in the queue.
    Each handoff is sent as a separate message with action buttons (Claim → Customer, Claim → AI, Info).
    Use this when the admin asks how many customers are waiting or wants to see the queue."""

    db = config["configurable"]["db"]
    staff_id = config["configurable"].get("staff_id")

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

    # Resolve staff phone for sending buttons
    staff_phone = None
    if staff_id:
        try:
            staff_record = await staff_service.get_staff_by_id(db, staff_id)
            staff_phone = staff_record.whatsapp_number
        except Exception:
            pass

    for h in handoffs:
        try:
            conv = await conversation_service.get_conversation_by_id(db, str(h.conversation_id))
            cust = await customer_service.get_customer_by_id(db, str(conv.customer_id))
            name = cust.display_name or cust.name
            phone = cust.whatsapp_number
        except Exception:
            name = "Unknown"
            phone = "N/A"

        wait_time = h.requested_at.strftime('%d-%m %H:%M') if h.requested_at else 'N/A'
        body = (
            f"*{name}* ({phone})\n"
            f"Reason: {h.reason or 'Not specified'}\n"
            f"Waiting since: {wait_time}"
        )

        # Send interactive buttons per handoff
        if staff_phone:
            try:
                handoff_short_id = str(h.id)[:8]
                await whatsapp_service.send_interactive_buttons(
                    to=staff_phone,
                    body=body,
                    buttons=[
                        {"id": f"claim_cust_{handoff_short_id}", "title": "Claim → Customer"},
                        {"id": f"claim_ai_{handoff_short_id}", "title": "Claim → AI"},
                    ],
                    header="Pending Handoff",
                )
            except Exception as exc:
                from loguru import logger as _log
                _log.error("get_pending_handoffs: failed to send buttons for handoff {} — {}", h.id, exc)

    return f"Sent *{len(handoffs)}* pending handoff(s) with action buttons."


@tool
async def get_all_handoffs(config: RunnableConfig, status: str = "") -> str:
    """View all handoff records with optional status filter.
    Use this when the admin asks for a full overview of all handoffs, handoff history, or wants to see everything.
    Args:
        status: Optional filter — "pending", "active", "resolved", "cancelled", or empty for all."""

    db = config["configurable"]["db"]

    filter_status = status.strip().lower() if status else None
    handoffs = await human_handoff_service.get_all_handoffs(db, status=filter_status)

    if not handoffs:
        label = f"No {filter_status} handoffs found." if filter_status else "No handoff records found."
        return label

    lines = []
    for h in handoffs:
        try:
            conv = await conversation_service.get_conversation_by_id(db, str(h.conversation_id))
            cust = await customer_service.get_customer_by_id(db, str(conv.customer_id))
            name = cust.display_name or cust.name
            phone = cust.whatsapp_number
        except Exception:
            name = "Unknown"
            phone = "N/A"

        staff_name = "Unassigned"
        if h.assigned_staff_id:
            try:
                staff_record = await staff_service.get_staff_by_id(db, str(h.assigned_staff_id))
                staff_name = staff_record.name
            except Exception:
                staff_name = "Unknown"

        lines.append(
            f"• *{name}* ({phone})\n"
            f"  Status: *{h.status}*\n"
            f"  Assigned to: {staff_name}\n"
            f"  Reason: {h.reason or 'Not specified'}\n"
            f"  Requested: {h.requested_at.strftime('%d-%m-%Y %H:%M') if h.requested_at else 'N/A'}"
        )

    header = f"*{len(handoffs)}* {filter_status or ''} handoff(s)".strip() + " (most recent):"
    return header + "\n\n" + "\n\n".join(lines)


@tool
async def get_active_handoffs(config: RunnableConfig) -> str:
    """View all currently active handoffs (staff currently chatting with customers).
    Use this when the admin asks who is currently being helped, which staff are busy, or active sessions."""

    db = config["configurable"]["db"]

    try:
        handoffs = await human_handoff_service.get_active_handoffs(db)
    except Exception:
        return "No active handoffs right now."

    lines = []
    for h in handoffs:
        try:
            conv = await conversation_service.get_conversation_by_id(db, str(h.conversation_id))
            cust = await customer_service.get_customer_by_id(db, str(conv.customer_id))
            name = cust.display_name or cust.name
            phone = cust.whatsapp_number
        except Exception:
            name = "Unknown"
            phone = "N/A"

        staff_name = "Unassigned"
        if h.assigned_staff_id:
            try:
                staff_record = await staff_service.get_staff_by_id(db, str(h.assigned_staff_id))
                staff_name = staff_record.name
            except Exception:
                staff_name = "Unknown"

        lines.append(
            f"• *{name}* ({phone})\n"
            f"  Handled by: *{staff_name}*\n"
            f"  Reason: {h.reason or 'Not specified'}\n"
            f"  Claimed at: {h.claimed_at.strftime('%d-%m-%Y %H:%M') if h.claimed_at else 'N/A'}"
        )

    return f"*{len(handoffs)}* active handoff(s):\n\n" + "\n\n".join(lines)


@tool
async def get_handoff_by_id(config: RunnableConfig, handoff_id: str) -> str:
    """Look up a specific handoff by its ID.
    Use this when the admin asks about a specific handoff or wants details on a particular handoff record."""

    db = config["configurable"]["db"]

    try:
        h = await human_handoff_service.get_handoffs_by_id(db, handoff_id)
    except Exception:
        return f"Handoff with ID {handoff_id} not found."

    try:
        conv = await conversation_service.get_conversation_by_id(db, str(h.conversation_id))
        cust = await customer_service.get_customer_by_id(db, str(conv.customer_id))
        name = cust.display_name or cust.name
        phone = cust.whatsapp_number
    except Exception:
        name = "Unknown"
        phone = "N/A"

    staff_name = "Unassigned"
    if h.assigned_staff_id:
        try:
            staff_record = await staff_service.get_staff_by_id(db, str(h.assigned_staff_id))
            staff_name = staff_record.name
        except Exception:
            staff_name = "Unknown"

    return (
        f"*Handoff Details*\n\n"
        f"• Customer: *{name}* ({phone})\n"
        f"• Status: *{h.status}*\n"
        f"• Assigned to: {staff_name}\n"
        f"• Triggered by: {h.triggered_by}\n"
        f"• Reason: {h.reason or 'Not specified'}\n"
        f"• Requested: {h.requested_at.strftime('%d-%m-%Y %H:%M') if h.requested_at else 'N/A'}\n"
        f"• Claimed: {h.claimed_at.strftime('%d-%m-%Y %H:%M') if h.claimed_at else 'N/A'}\n"
        f"• Resolved: {h.resolved_at.strftime('%d-%m-%Y %H:%M') if h.resolved_at else 'N/A'}"
    )


@tool
async def get_staff_handoffs(config: RunnableConfig, staff_name_or_id: str = "") -> str:
    """View handoff history for a specific staff member, or the current admin's own handoffs.
    Use this when the admin asks "show my handoffs", "what handoffs has [staff name] handled?", or similar.
    Args:
        staff_name_or_id: Staff member's name or ID. Leave empty to show the current admin's handoffs."""

    db = config["configurable"]["db"]
    staff_id = config["configurable"].get("staff_id")

    # If a name/ID was provided, try to find that staff member
    target_staff = None
    if staff_name_or_id.strip():
        # Try as ID first
        try:
            target_staff = await staff_service.get_staff_by_id(db, staff_name_or_id.strip())
        except Exception:
            # Try matching by name
            all_staff = await staff_service.get_all_staff(db)
            query = staff_name_or_id.strip().lower()
            for s in all_staff:
                if query in s.name.lower():
                    target_staff = s
                    break
            if not target_staff:
                return f"Could not find a staff member matching '{staff_name_or_id}'."
    elif staff_id:
        try:
            target_staff = await staff_service.get_staff_by_id(db, staff_id)
        except Exception:
            return "Could not identify your staff account."
    else:
        return "Please specify a staff member's name or ID."

    handoffs = await human_handoff_service.get_handoffs_by_staff_id(db, str(target_staff.id))

    if not handoffs:
        return f"No handoffs found for *{target_staff.name}*."

    lines = []
    for h in handoffs:
        try:
            conv = await conversation_service.get_conversation_by_id(db, str(h.conversation_id))
            cust = await customer_service.get_customer_by_id(db, str(conv.customer_id))
            name = cust.display_name or cust.name
        except Exception:
            name = "Unknown"

        lines.append(
            f"• *{name}* — {h.status}\n"
            f"  Reason: {h.reason or 'Not specified'}\n"
            f"  Requested: {h.requested_at.strftime('%d-%m-%Y %H:%M') if h.requested_at else 'N/A'}"
        )

    return f"*{len(handoffs)}* handoff(s) for *{target_staff.name}*:\n\n" + "\n\n".join(lines)


@tool
async def assign_handoff(config: RunnableConfig, staff_name_or_id: str) -> str:
    """Assign a pending handoff to a specific staff member.
    Use this when the admin wants to assign a waiting customer to a particular staff member instead of using the queue.
    Args:
        staff_name_or_id: The staff member's name or ID to assign the handoff to."""

    db = config["configurable"]["db"]

    # Find the target staff member
    target_staff = None
    try:
        target_staff = await staff_service.get_staff_by_id(db, staff_name_or_id.strip())
    except Exception:
        all_staff = await staff_service.get_all_staff(db)
        query = staff_name_or_id.strip().lower()
        for s in all_staff:
            if query in s.name.lower():
                target_staff = s
                break

    if not target_staff:
        return f"Could not find a staff member matching '{staff_name_or_id}'."

    # Find the oldest pending handoff
    try:
        pending = await human_handoff_service.get_pending_handoffs(db)
    except Exception:
        return "No pending handoffs to assign."

    oldest = pending[0]

    try:
        await human_handoff_service.assign_handoff_to_staff(db, str(oldest.id), str(target_staff.id))
        await conversation_service.activate_handoff_for_staff(db, str(oldest.conversation_id), str(target_staff.id))

        conv = await conversation_service.get_conversation_by_id(db, str(oldest.conversation_id))
        cust = await customer_service.get_customer_by_id(db, str(conv.customer_id))
        cust_name = cust.display_name or cust.name

        return (
            f"Handoff assigned to *{target_staff.name}*.\n\n"
            f"• Customer: *{cust_name}* ({cust.whatsapp_number})\n"
            f"• Reason: {oldest.reason or 'Not specified'}"
        )
    except Exception as exc:
        error_msg = str(exc)
        if ": " in error_msg:
            error_msg = error_msg.split(": ", 1)[1]
        return error_msg


# @tool
# async def delete_handoff(config: RunnableConfig, handoff_id: str) -> str:
#     """Permanently delete a handoff record.
#     Use this only when the admin explicitly asks to delete or remove a specific handoff from the system.
#     Args:
#         handoff_id: The ID of the handoff to delete."""

#     db = config["configurable"]["db"]

#     try:
#         await human_handoff_service.delete_handoff(db, handoff_id)
#         return f"Handoff {handoff_id} has been deleted."
#     except Exception:
#         return f"Could not delete handoff {handoff_id}. It may not exist."


@tool
async def send_mode_switch_button(config: RunnableConfig) -> str:
    """Send the mode switch button to the admin during an active handoff.
    Use this when the admin asks to see the mode switch button, wants to switch modes,
    or asks for the "talk to customer" / "talk to AI" button."""

    db = config["configurable"]["db"]
    staff_id = config["configurable"].get("staff_id")

    if not staff_id:
        return "Could not identify you."

    try:
        staff = await staff_service.get_staff_by_id(db, staff_id)
    except Exception:
        return "Could not find your staff account."

    current_mode = _get_staff_mode(staff_id)
    from ...services.whatsapp_staff_webhook_service import _send_mode_switch_button as _send_btn
    await _send_btn(staff.whatsapp_number, current_mode)

    mode_label = "AI" if current_mode == StaffChatMode.AI.value else "Customer"
    return f"Mode switch button sent. You're currently in *{mode_label} Mode*."


# Customer-facing handoff tools only
customer_handoff_tools = [
    request_human_agent,
    cancel_handoff_request,
]

# Staff/admin-only handoff tools
staff_handoff_tools = [
    confirm_resolve_handoff,
    resolve_handoff_request,
    check_handoff_status,
    claim_next_handoff,
    get_pending_handoffs,
    get_all_handoffs,
    get_active_handoffs,
    get_handoff_by_id,
    get_staff_handoffs,
    assign_handoff,
    send_mode_switch_button,
]

# All handoff tools (for backward compat if needed)
handoff_tools = customer_handoff_tools + staff_handoff_tools
