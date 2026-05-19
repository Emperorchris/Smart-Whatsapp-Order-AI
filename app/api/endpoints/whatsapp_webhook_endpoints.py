from fastapi import APIRouter, Request, Response
from ...core.dependencies import DBSession
from ...core import utils, exceptions
from ...services import (
    whatsapp_service,
    customer_service,
    conversation_service,
    message_service,
    processed_webhook_service,
)
from ...db.schemas.message_schema import MessageSchema
from ...db.schemas.customers_schema import CustomerSchema
from ...db.schemas.conversation_schema import ConversationSchema
from ...db.schemas.processed_webhook_schema import ProcessedWebhookSchema
from ...db.model import staff_model, human_hand_off_model
from sqlalchemy.orm import Session


whatsapp_webhook_router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp Webhook"])


@whatsapp_webhook_router.post("/")
async def whatsapp_webhook(db: DBSession, request: Request):
    form = await request.form()

    sender_from = form.get("From", "")
    body = form.get("Body", "")
    message_sid = form.get("MessageSid", "")
    raw_num_media = form.get("NumMedia", "0")
    try:
        num_media = max(int(raw_num_media or 0), 0)
    except (TypeError, ValueError):
        num_media = 0

    # 1. Prevent duplicate processing
    try:
        processed_webhook_service.get_processed_webhook_by_event_id(
            db, f"message_{message_sid}")
        return Response(content="", media_type="text/xml")
    except exceptions.NotFoundException:
        pass

    processed_webhook_service.create_processed_webhook(
        db, ProcessedWebhookSchema(source="twilio", event_id=f"message_{message_sid}")
    )

    # 2. Parse sender number and collect media dynamically
    sender_number = sender_from.replace("whatsapp:", "").strip()
    media_urls = [
        form.get(f"MediaUrl{i}")
        for i in range(num_media)
        if form.get(f"MediaUrl{i}")
    ]

    # Determine message type from all media content types
    def _resolve_message_type() -> str:
        if not num_media:
            return utils.MessageType.TEXT.value

        def _map_content_type(content_type: str) -> str:
            if content_type.startswith("image/"):
                return utils.MessageType.IMAGE.value
            if content_type.startswith("video/"):
                return utils.MessageType.VIDEO.value
            if content_type.startswith("audio/"):
                return utils.MessageType.AUDIO.value
            return utils.MessageType.DOCUMENT.value

        resolved_types = {
            _map_content_type((form.get(f"MediaContentType{i}", "") or "").strip().lower())
            for i in range(num_media)
        }

        if len(resolved_types) == 1:
            return next(iter(resolved_types))

        # Mixed media payloads are stored as document to keep a single enum value.
        return utils.MessageType.DOCUMENT.value

    message_type = _resolve_message_type()

    # 3. Identify sender — unknown numbers are treated as new customers
    try:
        sender_type = whatsapp_service.identify_sender(sender_number, db)
    except exceptions.NotFoundException:
        sender_type = utils.MessageSenderType.CUSTOMER.value

    # 4. Handle staff messages
    if sender_type == utils.MessageSenderType.STAFF.value:
        if body.strip().startswith("#"):
            # It's a command
            _handle_staff_command(db, sender_number, body.strip())
        else:
            # It's a regular message — forward to the customer
            _handle_staff_reply(db, sender_number, body.strip(), message_sid)
        return Response(content="", media_type="text/xml")

    # 5. Get or create customer
    try:
        customer = customer_service.get_customer_by_whatsapp_number(
            db, sender_number)
    except exceptions.NotFoundException:
        customer = customer_service.create_customer(
            db,
            CustomerSchema(
                whatsapp_number=sender_number,
            )
        )

    # 6. Get or create active conversation
    conversations = conversation_service.get_conversations_by_customer_id(
        db, str(customer.id))
    active_conversation = next(
        (c for c in conversations if c.status ==
         utils.ConversationStatus.ACTIVE.value),
        None
    )
    if not active_conversation:
        active_conversation = conversation_service.create_conversation(
            db,
            ConversationSchema(customer_id=customer.id)
        )

    # 7. Log inbound message
    message_service.create_message(db, MessageSchema(
        conversation_id=active_conversation.id,
        sender_type=utils.MessageSenderType.CUSTOMER.value,
        direction=utils.MessageDirection.INBOUND.value,
        message_type=message_type,
        content=body,
        media_urls=media_urls or None,
        status=utils.MessageStatus.DELIVERED.value,
        whatsapp_message_id=message_sid,
    ))

    # 8. If handoff is active, AI is disabled — do nothing, staff handles it
    if active_conversation.handoff_to_human:
        return Response(content="", media_type="text/xml")

    # 9. TODO: Run the LangGraph agent and send reply
    return Response(content="", media_type="text/xml")





def _handle_staff_reply(db: Session, staff_number: str, body: str, message_sid: str):
    """Forward a staff message to their assigned customer."""
    staff = db.query(staff_model.Staff).filter(
        staff_model.Staff.whatsapp_number == staff_number
    ).first()

    if not staff:
        return

    # Find the active handoff assigned to this staff
    active_handoff = db.query(human_hand_off_model.HumanHandOff).filter(
        human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
        human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
    ).first()

    if not active_handoff:
        whatsapp_service.send_message(
            to=staff_number,
            body="You have no active handoff. Your message was not delivered."
        )
        return

    # Get the customer's number from the conversation
    conversation = conversation_service.get_conversation_by_id(
        db, str(active_handoff.conversation_id)
    )
    
    customer = customer_service.get_customer_by_id(db, str(conversation.customer_id))

    # Send the message to the customer
    sent = whatsapp_service.send_message(to=customer.whatsapp_number, body=body)

    # Log the outbound message
    message_service.create_message(db, MessageSchema(
        conversation_id=active_handoff.conversation_id,
        sender_type=utils.MessageSenderType.STAFF.value,
        staff_id=staff.id,
        direction=utils.MessageDirection.OUTBOUND.value,
        message_type=utils.MessageType.TEXT.value,
        content=body,
        status=utils.MessageStatus.SENT.value,
        whatsapp_message_id=sent["sid"],
    ))

    # Log the inbound staff message too
    message_service.create_message(db, MessageSchema(
        conversation_id=active_handoff.conversation_id,
        sender_type=utils.MessageSenderType.STAFF.value,
        staff_id=staff.id,
        direction=utils.MessageDirection.INBOUND.value,
        message_type=utils.MessageType.TEXT.value,
        content=body,
        status=utils.MessageStatus.DELIVERED.value,
        whatsapp_message_id=message_sid,
    ))


def _handle_staff_command(db: Session, staff_number: str, command: str):
    """Handle commands sent by staff via WhatsApp."""
    from ...services import human_handoff_service

    staff = db.query(staff_model.Staff).filter(
        staff_model.Staff.whatsapp_number == staff_number
    ).first()

    if not staff:
        return

    if command == utils.StaffConversationCommand.DONE.value:
        # Resolve active handoff and re-enable AI
        active_handoff = db.query(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
        ).first()

        if active_handoff:
            conversation_service.resume_ai(db, str(active_handoff.conversation_id))
            whatsapp_service.send_message(
                to=staff_number,
                body="✅ Handoff resolved. AI has resumed for this conversation."
            )
        else:
            whatsapp_service.send_message(
                to=staff_number,
                body="You have no active handoff to resolve."
            )

    elif command == utils.StaffConversationCommand.NEXT.value:
        # Claim the next pending handoff in the queue
        try:
            handoff = human_handoff_service.claim_next_pending_handoff(db, str(staff.id))
            conversation_service.activate_handoff_for_staff(
                db, str(handoff.conversation_id), str(staff.id)
            )
            whatsapp_service.send_message(
                to=staff_number,
                body=(
                    f"📩 You've been assigned a new customer.\n"
                    f"Conversation ID: {handoff.conversation_id}\n"
                    f"Reason: {handoff.reason or 'Not specified'}"
                )
            )
        except Exception as e:
            whatsapp_service.send_message(
                to=staff_number,
                body=f"Could not claim next handoff: {str(e)}"
            )

    elif command == utils.StaffConversationCommand.QUEUE.value:
        # Show pending handoffs count
        pending = db.query(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.status.in_([
                utils.HandOffStatus.REQUESTED.value,
                utils.HandOffStatus.PENDING.value,
            ])
        ).count()
        whatsapp_service.send_message(
            to=staff_number,
            body=f"📋 There are *{pending}* customer(s) waiting in the queue."
        )

    elif command == utils.StaffConversationCommand.SKIP.value:
        # Release current active handoff back to the queue
        active_handoff = db.query(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
        ).first()

        if active_handoff:
            active_handoff.assigned_staff_id = None
            active_handoff.status = utils.HandOffStatus.PENDING.value
            active_handoff.claimed_at = None
            db.commit()
            whatsapp_service.send_message(
                to=staff_number,
                body="↩️ Handoff returned to the queue. Another agent can pick it up."
            )
        else:
            whatsapp_service.send_message(
                to=staff_number,
                body="You have no active handoff to skip."
            )

    elif command == utils.StaffConversationCommand.INFO.value:
        # Show current active handoff details
        active_handoff = db.query(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
        ).first()

        if active_handoff:
            whatsapp_service.send_message(
                to=staff_number,
                body=(
                    f"ℹ️ *Active Handoff Info*\n"
                    f"Conversation ID: {active_handoff.conversation_id}\n"
                    f"Reason: {active_handoff.reason or 'Not specified'}\n"
                    f"Status: {active_handoff.status} \n"
                    f"Triggered by: {active_handoff.triggered_by}\n"
                    f"Requested at: {active_handoff.requested_at.strftime('%d-%m-%Y %H:%M')}"
                    
                )
            )
        else:
            whatsapp_service.send_message(
                to=staff_number,
                body="You have no active handoff at the moment."
            )

    else:
        whatsapp_service.send_message(
            to=staff_number,
            body=(
                "Available commands:\n"
                f"{utils.StaffConversationCommand.NEXT.value} — claim the next customer\n"
                f"{utils.StaffConversationCommand.DONE.value} — resolve your current handoff\n"
                f"{utils.StaffConversationCommand.SKIP.value} — return handoff to queue\n"
                f"{utils.StaffConversationCommand.QUEUE.value} — see how many customers are waiting\n"
                f"{utils.StaffConversationCommand.INFO.value} — view your current handoff details"
            )
        )
