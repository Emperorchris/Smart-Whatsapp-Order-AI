import asyncio
import re
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

from ..core import utils
from ..db.schemas.message_schema import MessageSchema
from ..ai.graph import agent_graph
from ..ai.memory.conversation_memory import load_conversation_history, save_agent_messages
from .whatsapp_webhook_processing_service import IncomingWhatsAppPayload
from ..db.schemas.customers_schema import CustomerResponse
from ..db.schemas.conversation_schema import ConversationResponse
from . import message_service, whatsapp_service, whatsapp_webhook_processing_service

logger = logging.getLogger(__name__)


async def process_customer_message(
    db: AsyncSession,
    payload: IncomingWhatsAppPayload,
    customer: CustomerResponse,
    active_conversation: ConversationResponse,
):
    """Process a single customer message: resolve context, run the AI agent, and send the reply."""

    # If the user replied to a specific message, resolve what they're referring to
    reply_context = await whatsapp_webhook_processing_service.resolve_reply_context(
        db, payload.reply_to_message_id
    )
    if reply_context:
        payload.body = (
            f'[Customer replied to this message: "{reply_context}"]\n\n'
            f"{payload.body}"
        )

    # Log inbound message
    await whatsapp_webhook_processing_service.log_inbound_message(
        db,
        active_conversation.id,
        utils.MessageDirection.INBOUND.value,
        payload,
    )

    # If handoff is active, AI is disabled
    if active_conversation.handoff_to_human:
        return

    # Run the LangGraph agent
    history = await load_conversation_history(db, str(active_conversation.id))
    initial_state = {
        "messages": history,
        "customer_whatsapp_number": payload.sender_number,
        "customer_name": payload.profile_name,
        "customer_display_name": payload.profile_name,
        "customer_wa_id": payload.wa_id,
        "customer_id": str(customer.id),
        "conversation_id": str(active_conversation.id),
    }

    history_count = len(initial_state["messages"])

    result = await agent_graph.run_agent(
        initial_state,
        db=db,
        customer_id=str(customer.id),
        conversation_id=str(active_conversation.id),
    )

    ai_reply = (
        result["messages"][-1].content
        if result["messages"]
        else "Sorry, I couldn't process your request right now."
    )

    # Only scan NEW messages from this agent run (not loaded history)
    new_messages = result["messages"][history_count:]

    await save_agent_messages(db, str(active_conversation.id), new_messages)

    # Extract per-product blocks from new messages (ToolMessages have product data)
    product_blocks = _extract_product_blocks(new_messages)

    # Clean all product/media blocks from the final AI reply
    ai_reply = re.sub(r"\[PRODUCT_START\].*?\[PRODUCT_END\]", "", ai_reply, flags=re.DOTALL)
    ai_reply = re.sub(r"\n*\[PRODUCT_MEDIA\].*?\[/PRODUCT_MEDIA\]", "", ai_reply)
    ai_reply = re.sub(r"\n*\[MEDIA_URLS\].*?\[/MEDIA_URLS\]", "", ai_reply)
    ai_reply = ai_reply.strip()

    # If there are product blocks, merge the AI follow-up into the last block's caption
    # so the customer sees one message instead of a duplicate
    if product_blocks and ai_reply:
        last_text, last_media = product_blocks[-1]
        product_blocks[-1] = (f"{last_text}\n\n{ai_reply}", last_media)
        ai_reply = ""

    await _send_reply(db, payload, active_conversation, ai_reply, product_blocks)


async def _send_reply(
    db: AsyncSession,
    payload: IncomingWhatsAppPayload,
    active_conversation: ConversationResponse,
    ai_reply: str,
    product_blocks: list[tuple[str, list[str]]],
):
    """Send the AI reply (with product media if any) back to the customer via WhatsApp."""
    try:
        if product_blocks:
            # Send all product blocks concurrently
            async def _send_block(block_text: str, block_media: list[str]):
                if block_media:
                    return block_text, await whatsapp_service.send_product_message(
                        to=payload.sender_number, caption=block_text, media_urls=block_media,
                    )
                return block_text, await whatsapp_service.send_message(
                    to=payload.sender_number, body=block_text,
                )

            results = await asyncio.gather(
                *[_send_block(text, media) for text, media in product_blocks],
                return_exceptions=True,
            )

            # Save wamids for reply-to-message tracking
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("Failed to send product block: %s", result)
                    continue
                block_text, result_msg = result
                wamid = result_msg.get("message_id") or (result_msg.get("media_ids") or [None])[-1]
                if wamid:
                    await message_service.create_message(
                        db,
                        MessageSchema(
                            conversation_id=active_conversation.id,
                            sender_type=utils.MessageSenderType.AI.value,
                            direction=utils.MessageDirection.OUTBOUND.value,
                            message_type=utils.MessageType.TEXT.value,
                            content=block_text,
                            whatsapp_message_id=wamid,
                            status=utils.MessageStatus.SENT.value,
                        ),
                    )

            if ai_reply:
                await whatsapp_service.send_message(
                    to=payload.sender_number,
                    body=ai_reply,
                )
        else:
            await whatsapp_service.send_message(
                to=payload.sender_number,
                body=ai_reply,
            )
    except Exception as exc:
        logger.error("Failed to send reply to %s: %s", payload.sender_number, exc)


def _extract_product_blocks(messages: list) -> list[tuple[str, list[str]]]:
    """Parse tool messages for [PRODUCT_START]...[PRODUCT_END] blocks.
    Returns a list of (product_text, [media_urls]) tuples."""
    blocks: list[tuple[str, list[str]]] = []

    for msg in messages:
        # ToolMessage content can be a string or list — normalize it
        raw = getattr(msg, "content", "") or ""
        if isinstance(raw, list):
            content = " ".join(str(item) for item in raw)
        else:
            content = str(raw)

        if "[PRODUCT_START]" not in content:
            continue

        # Find all product blocks in this message
        product_matches = re.findall(
            r"\[PRODUCT_START\]\s*(.*?)\s*\[PRODUCT_END\]", content, re.DOTALL
        )

        for block in product_matches:
            # Extract media URLs from this block
            media_match = re.search(r"\[PRODUCT_MEDIA\](.*?)\[/PRODUCT_MEDIA\]", block)
            media_urls = []
            if media_match:
                media_urls = [u.strip() for u in media_match.group(1).split(",") if u.strip()]

            # Clean the block text (remove media tags)
            clean_text = re.sub(r"\n*\[PRODUCT_MEDIA\].*?\[/PRODUCT_MEDIA\]", "", block).strip()

            if clean_text:
                blocks.append((clean_text, media_urls))

    return blocks
