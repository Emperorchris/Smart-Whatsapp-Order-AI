import asyncio
from loguru import logger
from fastapi import APIRouter, Request, Response
from ...core.dependencies import DBSession
from ...core.rate_limiter import limiter
from ...core.config import Config
from ...core import utils, exceptions
from ...db.db_engine import AsyncSessionLocal
from ...services import (
    whatsapp_service,
    whatsapp_staff_webhook_service,
    whatsapp_webhook_processing_service,
    customer_message_handler_service,
)


# logger = logging.getLogger(__name__)

# Per-conversation locks to prevent concurrent processing of messages
# from the same customer (avoids response mixing/race conditions)
_conversation_locks: dict[str, asyncio.Lock] = {}

whatsapp_webhook_router = APIRouter(
    prefix="/webhooks/whatsapp", tags=["WhatsApp Webhook"]
)


# ──────────────────────────────────────────────────────────────
# GET — Meta webhook verification
# ──────────────────────────────────────────────────────────────

@whatsapp_webhook_router.get("")
async def verify_webhook(request: Request):
    """Meta sends a GET request to verify the webhook URL during setup.
    We must return the hub.challenge value if the verify token matches."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == Config.META_WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Webhook verification failed. Token mismatch.")
    return Response(content="Forbidden", status_code=403)


# ──────────────────────────────────────────────────────────────
# POST — Incoming messages from Meta Cloud API
# ──────────────────────────────────────────────────────────────

@whatsapp_webhook_router.post("")
@limiter.limit("60/minute")
async def whatsapp_webhook(request: Request, db: DBSession):
    body = await request.json()

    # Meta sends status updates too (delivered, read, etc.) — ignore those
    payload = whatsapp_webhook_processing_service.parse_incoming_payload(body)
    if not payload:
        return Response(content="OK", status_code=200)

    # 1. Prevent duplicate processing
    is_new_event = await whatsapp_webhook_processing_service.ensure_not_duplicate_event(
        db, payload.message_sid
    )
    if not is_new_event:
        return Response(content="OK", status_code=200)

    # 2. Identify sender — unknown numbers are treated as new customers
    try:
        sender_type = await whatsapp_service.identify_sender(payload.sender_number, db)
    except exceptions.NotFoundException:
        sender_type = utils.MessageSenderType.CUSTOMER.value

    logger.info("webhook: sender={} identified as {}", payload.sender_number, sender_type)

    # 3. Handle staff messages — staff should never be created as customers.
    #    All staff processing (AI, handoff forwarding) happens inside
    #    handle_staff_incoming_message. Run in background so Meta gets 200 fast.
    if sender_type == utils.MessageSenderType.STAFF.value:
        asyncio.create_task(
            _process_staff_message_background(payload)
        )
        return Response(content="OK", status_code=200)

    # 4. Get or create customer (returns None if sender is a staff member)
    customer = await whatsapp_webhook_processing_service.get_or_create_customer(db, payload)
    if customer is None:
        logger.info("webhook: sender {} is a staff member, skipping customer creation", payload.sender_number)
        return Response(content="OK", status_code=200)

    # 5. Get or create active conversation
    active_conversation = (
        await whatsapp_webhook_processing_service.get_or_create_active_conversation(
            db, str(customer.id)
        )
    )

    # 6. Process in background — return 200 IMMEDIATELY so Meta doesn't retry
    asyncio.create_task(
        _process_message_background(payload, customer, active_conversation, sender_type)
    )

    return Response(content="OK", status_code=200)


async def _process_staff_message_background(payload):
    """Process a staff message in the background with its own DB session."""
    async with AsyncSessionLocal() as db:
        try:
            await whatsapp_staff_webhook_service.handle_staff_incoming_message(
                db,
                payload.sender_number,
                payload.body,
                payload.message_sid,
                interactive_id=payload.interactive_id,
            )
        except Exception:
            logger.opt(exception=True).error(
                "Background staff message processing failed: sender={}, body={!r}",
                payload.sender_number, payload.body[:100],
            )


async def _process_message_background(payload, customer, active_conversation, sender_type=utils.MessageSenderType.CUSTOMER.value):
    """Process the customer message in the background with its own DB session."""
    async with AsyncSessionLocal() as db:
        conv_key = str(active_conversation.id)
        if conv_key not in _conversation_locks:
            _conversation_locks[conv_key] = asyncio.Lock()

        lock = _conversation_locks[conv_key]
        try:
            async with lock:
                await customer_message_handler_service.process_customer_message(
                    db, payload, customer, active_conversation, sender_type
                )
        except Exception:
            logger.opt(exception=True).error(
                "Background message processing failed: customer={}, conversation={}, body={!r}",
                str(customer.id), conv_key, payload.body[:100],
            )
        finally:
            if not lock.locked():
                _conversation_locks.pop(conv_key, None)








# ──────────────────────────────────────────────────────────────
# Twilio webhook endpoint (commented out — kept for reference)
# ──────────────────────────────────────────────────────────────

# @whatsapp_webhook_router.post("")
# async def whatsapp_webhook(db: DBSession, request: Request):
#     form = await request.form()
#
#     payload = whatsapp_webhook_processing_service.parse_incoming_payload(form)
#
#     # 1. Prevent duplicate processing
#     is_new_event = whatsapp_webhook_processing_service.ensure_not_duplicate_event(
#         db, payload.message_sid
#     )
#     if not is_new_event:
#         return Response(content="", media_type="text/xml")
#
#     # 3. Identify sender — unknown numbers are treated as new customers
#     try:
#         sender_type = whatsapp_service.identify_sender(payload.sender_number, db)
#     except exceptions.NotFoundException:
#         sender_type = utils.MessageSenderType.CUSTOMER.value
#
#     # 4. Handle staff messages
#     if sender_type == utils.MessageSenderType.STAFF.value:
#         whatsapp_staff_webhook_service.handle_staff_incoming_message(
#             db,
#             payload.sender_number,
#             payload.body,
#             payload.message_sid,
#         )
#         return Response(content="", media_type="text/xml")
#
#     # 5. Get or create customer
#     customer = whatsapp_webhook_processing_service.get_or_create_customer(db, payload)
#
#     # 6. Get or create active conversation
#     active_conversation = (
#         whatsapp_webhook_processing_service.get_or_create_active_conversation(
#             db, str(customer.id)
#         )
#     )
#
#     # 7. Log message
#     whatsapp_webhook_processing_service.log_inbound_message(
#         db,
#         active_conversation.id,
#         utils.MessageDirection.INBOUND.value,
#         payload,
#     )
#
#     # 8. If handoff is active, AI is disabled — do nothing, staff handles it
#     if active_conversation.handoff_to_human:
#         return Response(content="", media_type="text/xml")
#
#     # 9. Run the LangGraph agent and send reply
#     history = load_conversation_history(db, str(active_conversation.id))
#     initial_state = {
#         "messages": history,
#         "customer_whatsapp_number": payload.sender_number,
#         "customer_name": payload.profile_name,
#         "customer_display_name": payload.profile_name,
#         "customer_wa_id": payload.wa_id,
#         "customer_id": str(customer.id),
#         "conversation_id": str(active_conversation.id),
#     }
#
#     result = agent_graph.run_agent(
#         initial_state,
#         db=db,
#         customer_id=str(customer.id),
#         conversation_id=str(active_conversation.id),
#     )
#
#     ai_reply = (
#         result["messages"][-1].content
#         if result["messages"]
#         else "Sorry, I couldn't process your request right now."
#     )
#
#     # Extract media URLs from tool results embedded in messages
#     media_urls = []
#     for msg in result["messages"]:
#         content = getattr(msg, "content", "") or ""
#         match = re.search(r"\[MEDIA_URLS\](.*?)\[/MEDIA_URLS\]", content)
#         if match:
#             media_urls.extend(match.group(1).split(","))
#
#     # Clean the tag from the final reply so the customer doesn't see it
#     ai_reply = re.sub(r"\n*\[MEDIA_URLS\].*?\[/MEDIA_URLS\]", "", ai_reply).strip()
#
#     whatsapp_service.send_message(
#         to=payload.sender_number,
#         body=ai_reply,
#         media_urls=media_urls[:10] if media_urls else None,
#     )
#
#     whatsapp_webhook_processing_service.log_outbound_message(
#         db,
#         conversation_id=active_conversation.id,
#         content=ai_reply,
#         media_urls=media_urls if media_urls else None,
#     )
#
#     return Response(content=ai_reply, media_type="text/xml")
