from sqlalchemy.orm import Session

from ..core import utils
from ..db.model import human_hand_off_model, staff_model
from ..db.schemas.message_schema import MessageSchema
from . import (
    conversation_service,
    customer_service,
    human_handoff_service,
    message_service,
    whatsapp_service,
)


def handle_staff_incoming_message(db: Session, staff_number: str, body: str, message_sid: str) -> None:
    clean_body = body.strip()
    if clean_body.startswith("#"):
        _handle_staff_command(db, staff_number, clean_body)
        return

    _handle_staff_reply(db, staff_number, clean_body, message_sid)


def _handle_staff_reply(db: Session, staff_number: str, body: str, message_sid: str) -> None:
    """Forward a staff message to their assigned customer."""
    staff = db.query(staff_model.Staff).filter(
        staff_model.Staff.whatsapp_number == staff_number
    ).first()

    if not staff:
        return

    active_handoff = db.query(human_hand_off_model.HumanHandOff).filter(
        human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
        human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
    ).first()

    if not active_handoff:
        whatsapp_service.send_message(
            to=staff_number,
            body="You have no active handoff. Your message was not delivered.",
        )
        return

    conversation = conversation_service.get_conversation_by_id(
        db, str(active_handoff.conversation_id)
    )
    customer = customer_service.get_customer_by_id(
        db, str(conversation.customer_id))

    sent = whatsapp_service.send_message(
        to=customer.whatsapp_number, body=body)

    message_service.create_message(
        db,
        MessageSchema(
            conversation_id=active_handoff.conversation_id,
            sender_type=utils.MessageSenderType.STAFF.value,
            staff_id=staff.id,
            direction=utils.MessageDirection.OUTBOUND.value,
            message_type=utils.MessageType.TEXT.value,
            content=body,
            status=utils.MessageStatus.SENT.value,
            whatsapp_message_id=sent["sid"],
        ),
    )

    message_service.create_message(
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


def _handle_staff_command(db: Session, staff_number: str, command: str) -> None:
    """Handle commands sent by staff via WhatsApp."""
    staff = db.query(staff_model.Staff).filter(
        staff_model.Staff.whatsapp_number == staff_number
    ).first()

    if not staff:
        return

    if command == utils.StaffConversationCommand.DONE.value:
        active_handoff = db.query(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
        ).first()

        if active_handoff:
            conversation_service.resume_ai(
                db, str(active_handoff.conversation_id))
            whatsapp_service.send_message(
                to=staff_number,
                body="✅ Handoff resolved. AI has resumed for this conversation.",
            )
        else:
            whatsapp_service.send_message(
                to=staff_number,
                body="You have no active handoff to resolve.",
            )

    elif command == utils.StaffConversationCommand.NEXT.value:
        try:
            handoff = human_handoff_service.claim_next_pending_handoff(
                db, str(staff.id))
            conversation_service.activate_handoff_for_staff(
                db, str(handoff.conversation_id), str(staff.id)
            )
            whatsapp_service.send_message(
                to=staff_number,
                body=(
                    f"📩 You've been assigned a new customer.\n"
                    f"Conversation ID: {handoff.conversation_id}\n"
                    f"Reason: {handoff.reason or 'Not specified'}"
                ),
            )
        except Exception as exc:
            whatsapp_service.send_message(
                to=staff_number,
                body=f"Could not claim next handoff: {str(exc)}",
            )

    elif command == utils.StaffConversationCommand.QUEUE.value:
        pending = db.query(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.status.in_(
                [utils.HandOffStatus.REQUESTED.value,
                    utils.HandOffStatus.PENDING.value]
            )
        ).count()
        whatsapp_service.send_message(
            to=staff_number,
            body=f"📋 There are *{pending}* customer(s) waiting in the queue.",
        )

    elif command == utils.StaffConversationCommand.SKIP.value:
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
                body="↩️ Handoff returned to the queue. Another agent can pick it up.",
            )
        else:
            whatsapp_service.send_message(
                to=staff_number,
                body="You have no active handoff to skip.",
            )

    elif command == utils.StaffConversationCommand.INFO.value:
        active_handoff = db.query(human_hand_off_model.HumanHandOff).filter(
            human_hand_off_model.HumanHandOff.assigned_staff_id == staff.id,
            human_hand_off_model.HumanHandOff.status == utils.HandOffStatus.ACTIVE.value,
        ).first()

        if active_handoff:
            whatsapp_service.send_message(
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
            whatsapp_service.send_message(
                to=staff_number,
                body="You have no active handoff at the moment.",
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
            ),
        )
