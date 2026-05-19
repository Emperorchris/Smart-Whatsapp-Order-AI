import os
from typing import Any

from sqlalchemy.orm import Session
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from ..core import exceptions
from ..core.config import Config
from ..db.model import customer_model, staff_model
from ..core import utils
from ..db.schemas import message_schema


def _format_twilio_whatsapp(number: str) -> str:
	if not number or not number.strip():
		raise exceptions.BadRequestException("A valid WhatsApp number is required.")

	value = number.strip()
	if value.lower().startswith("whatsapp:"):
		return value

	return f"whatsapp:{value}"


def _get_twilio_client() -> Client:
	account_sid = Config.TWILIO_ACCOUNT_SID or os.getenv("TWILIO_ACCOUNT_SID")
	auth_token = Config.TWILIO_AUTH_TOKEN or os.getenv("TWILIO_AUTH_TOKEN")

	if not account_sid or not auth_token:
		raise exceptions.InternalServerException(
			"Twilio credentials are not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
		)

	return Client(account_sid, auth_token)


def send_message(to: str, body: str, media_urls: list[str] | None = None) -> dict[str, Any]:
	if not body or not body.strip():
		raise exceptions.BadRequestException("Message body cannot be empty.")

	from_number = Config.TWILIO_WHATSAPP_NUMBER or os.getenv("TWILIO_WHATSAPP_NUMBER")
	if not from_number:
		raise exceptions.InternalServerException(
			"Twilio WhatsApp sender is not configured. Set TWILIO_WHATSAPP_NUMBER."
		)

	client = _get_twilio_client()

	try:
		message = client.messages.create(
			from_=_format_twilio_whatsapp(from_number),
			to=_format_twilio_whatsapp(to),
			body=body.strip(),
			media_url=media_urls or [],
		)
	except TwilioRestException as exc:
		raise exceptions.BadRequestException("Failed to send WhatsApp message.", error_detail=str(exc))

	return {
		"sid": message.sid,
		"status": message.status,
		"to": message.to,
		"from": message.from_,
	}


def identify_sender(phone: str, db: Session) -> str:
	if not phone or not phone.strip():
		raise exceptions.BadRequestException("Sender phone number is required.")

	phone_value = phone.strip()
	if phone_value.lower().startswith("whatsapp:"):
		phone_value = phone_value.split(":", 1)[1]

	staff = db.query(staff_model.Staff).filter(
		staff_model.Staff.is_active.is_(True),
		staff_model.Staff.whatsapp_number.is_not(None),
		staff_model.Staff.whatsapp_number == phone_value,
	).all()

	if staff:
		return utils.MessageSenderType.STAFF.value

	customer = db.query(customer_model.Customer).filter(
		customer_model.Customer.whatsapp_number == phone_value
	).all()
	if customer:
		return utils.MessageSenderType.CUSTOMER.value

	raise exceptions.NotFoundException("Sender is not a registered customer or staff member.")


def notify_all_staff(db: Session, message: str, customer_id: str | None = None) -> dict[str, Any]:
	if not message or not message.strip():
		raise exceptions.BadRequestException("Notification message cannot be empty.")

	
	full_message = message.strip()
	if customer_id:
		customer = db.query(customer_model.Customer).filter(
			customer_model.Customer.id == customer_id
		).first()
		if customer:
			full_message += (
				f"\n\n👤 *Customer Details*"
				f"\nName: {customer.name}"
				f"\nWhatsApp: {customer.whatsapp_number}"
				f"\nSegment: {customer.customer_segment or 'N/A'}"
				f"\nStatus: {customer.customer_status}"
			)
			if customer.email:
				full_message += f"\nEmail: {customer.email}"

	recipients = db.query(staff_model.Staff).filter(
		staff_model.Staff.is_active.is_(True),
		staff_model.Staff.whatsapp_number.is_not(None),
	).all()

	sent_count = 0
	failed: list[dict[str, str, str]] = []

	for member in recipients:
		try:
			send_message(to=member.whatsapp_number, body=full_message)
			sent_count += 1
		except Exception as exc:
			failed.append({"staff_id": str(member.id), "staff_name": member.name, "error": str(exc)})

	return {
		"total_recipients": len(recipients),
		"sent_count": sent_count,
		"failed_count": len(failed),
		"failed": failed,
	}
 
