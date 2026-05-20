from fastapi import APIRouter, Request, Response
from langchain_core.messages import HumanMessage
from ...core.dependencies import DBSession
from ...core import utils, exceptions
from ...services import (
    whatsapp_service,
    whatsapp_staff_webhook_service,
    whatsapp_webhook_processing_service,
)
from ...ai.graph import agent_graph


whatsapp_webhook_router = APIRouter(
    prefix="/webhooks/whatsapp", tags=["WhatsApp Webhook"]
)


@whatsapp_webhook_router.post("")
async def whatsapp_webhook(db: DBSession, request: Request):
    form = await request.form()

    payload = whatsapp_webhook_processing_service.parse_incoming_payload(form)

    # 1. Prevent duplicate processing
    is_new_event = whatsapp_webhook_processing_service.ensure_not_duplicate_event(
        db, payload.message_sid
    )
    if not is_new_event:
        return Response(content="", media_type="text/xml")

    # 3. Identify sender — unknown numbers are treated as new customers
    try:
        sender_type = whatsapp_service.identify_sender(payload.sender_number, db)
    except exceptions.NotFoundException:
        sender_type = utils.MessageSenderType.CUSTOMER.value

    # 4. Handle staff messages
    if sender_type == utils.MessageSenderType.STAFF.value:
        whatsapp_staff_webhook_service.handle_staff_incoming_message(
            db,
            payload.sender_number,
            payload.body,
            payload.message_sid,
        )
        return Response(content="", media_type="text/xml")

    # 5. Get or create customer
    customer = whatsapp_webhook_processing_service.get_or_create_customer(db, payload)

    # 6. Get or create active conversation
    active_conversation = (
        whatsapp_webhook_processing_service.get_or_create_active_conversation(
            db, str(customer.id)
        )
    )

    # 7. Log inbound message
    whatsapp_webhook_processing_service.log_customer_inbound_message(
        db,
        active_conversation.id,
        payload,
    )

    # 8. If handoff is active, AI is disabled — do nothing, staff handles it
    if active_conversation.handoff_to_human:
        return Response(content="", media_type="text/xml")

    # 9. TODO: Run the LangGraph agent and send reply
    initial_state = {
        "messages": [HumanMessage(content=payload.body)],
        "customer_whatsapp_number": payload.sender_number,
        "customer_name": payload.profile_name,
        "customer_display_name": payload.profile_name,
        "customer_wa_id": payload.wa_id,
        "customer_id": str(customer.id),
        "conversation_id": str(active_conversation.id),
    }
    
    result = agent_graph.run_agent(initial_state, db=db)
    
    ai_reply = result["messages"][-1].content if result["messages"] else "Sorry, I couldn't process your request right now."
    
    whatsapp_service.send_message(
        to=payload.sender_number,
        body=ai_reply,
    )
    
    # whatsapp_webhook_processing_service.log_customer_outbound_message(
    #     db,
    #     active_conversation.id,
    #     ai_reply,
    # )
    
    return Response(content=ai_reply, media_type="text/xml")