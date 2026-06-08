import uuid as uuid_mod
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    AnyMessage,
)
from ...db.model.message_model import Message
from ...db.model.conversation_model import Conversation
from ...core.utils import (
    MessageDirection,
    MessageSenderType,
    MessageStatus,
    MessageType,
)


# Keep last N raw messages — older ones get summarized
RECENT_RAW_MESSAGES = 6
# Trigger summarization when total messages exceed this threshold
SUMMARIZE_THRESHOLD = 10


async def load_conversation_history(
    db: AsyncSession, conversation_id: str
) -> list[AnyMessage]:
    """Load conversation history with summarization.
    Returns: [summary_message (if exists)] + [last N raw messages]
    """
    # Get the conversation's existing summary
    conv_result = await db.execute(
        select(Conversation).filter(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalars().first()
    summary = conversation.summary if conversation else None
    summary_count = (conversation.summary_message_count or 0) if conversation else 0

    # Count total messages
    count_result = await db.execute(
        select(func.count()).select_from(Message).filter(
            Message.conversation_id == conversation_id
        )
    )
    total_messages = count_result.scalar() or 0

    # Load recent raw messages
    result = await db.execute(
        select(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(RECENT_RAW_MESSAGES)
    )
    rows = list(reversed(result.scalars().all()))

    # If we have enough messages and no summary yet (or summary is stale), generate one
    older_unsummarized = total_messages - len(rows)
    if older_unsummarized > 0 and older_unsummarized > summary_count:
        try:
            await _generate_summary(db, conversation_id, total_messages - len(rows))

            # Reload the summary
            conv_result = await db.execute(
                select(Conversation).filter(Conversation.id == conversation_id)
            )
            conversation = conv_result.scalars().first()
            summary = conversation.summary if conversation else None
        except Exception:
            logger.opt(exception=True).warning(
                "conversation_memory: summarization failed for conversation={}, skipping",
                conversation_id,
            )

    # Build message list
    messages: list[AnyMessage] = []

    # Prepend summary as context if available
    if summary:
        messages.append(HumanMessage(
            content=f"[Conversation summary so far: {summary}]"
        ))

    # Add recent raw messages
    for row in rows:
        content = row.content or ""

        if row.message_type == MessageType.TOOL_CALL.value:
            tool_calls = []
            if row.tool_metadata and isinstance(row.tool_metadata, list):
                tool_calls = row.tool_metadata
            msg = AIMessage(content=content, tool_calls=tool_calls)
            messages.append(msg)

        elif row.message_type == MessageType.TOOL_RESULT.value:
            meta = {}
            if row.tool_metadata and isinstance(row.tool_metadata, dict):
                meta = row.tool_metadata
            msg = ToolMessage(
                content=content,
                tool_call_id=meta.get("tool_call_id", str(uuid_mod.uuid4())),
                name=meta.get("tool_name", "unknown"),
            )
            messages.append(msg)

        elif row.direction == MessageDirection.INBOUND.value:
            messages.append(HumanMessage(content=content))

        else:
            messages.append(AIMessage(content=content))

    return _sanitize_message_sequence(messages)


async def _generate_summary(
    db: AsyncSession, conversation_id: str, message_count: int
) -> None:
    """Generate a rule-based summary from older messages (no LLM call needed)."""
    # Load the older messages that need summarizing
    result = await db.execute(
        select(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(message_count)
    )
    rows = result.scalars().all()

    if not rows:
        return

    # Extract key facts from messages
    facts = []
    for row in rows:
        content = (row.content or "").strip()
        if not content:
            continue

        # Customer messages — capture what they asked for
        if row.direction == MessageDirection.INBOUND.value:
            # Skip system-injected messages
            if content.startswith("[Customer selected") or content.startswith("[Customer wants"):
                continue
            if len(content) > 5:
                facts.append(f"Customer: {content[:100]}")

        # AI text responses — capture key info
        elif row.message_type == MessageType.TEXT.value and row.sender_type == MessageSenderType.AI.value:
            # Extract order numbers
            if "#ORD-" in content:
                import re
                orders = re.findall(r"#ORD-\d+", content)
                for order in orders:
                    facts.append(f"Order placed: {order}")
            # Extract cart actions
            elif "added" in content.lower() and "cart" in content.lower():
                facts.append(f"AI: {content[:80]}")

        # Tool results — extract key outcomes
        elif row.message_type == MessageType.TOOL_RESULT.value:
            if "Address saved" in content:
                # Extract address from tool result
                lines = content.split("\n")
                addr_parts = [line.strip("• ").strip() for line in lines if line.strip().startswith("•")]
                if addr_parts:
                    facts.append(f"Address saved: {', '.join(addr_parts[:3])}")
            elif "Order placed" in content or "order_number" in content.lower():
                import re
                orders = re.findall(r"#?ORD-\d+", content)
                if orders:
                    facts.append(f"Order created: {orders[0]}")

    if not facts:
        return

    # Deduplicate and limit
    seen = set()
    unique_facts = []
    for f in facts:
        key = f[:50].lower()
        if key not in seen:
            seen.add(key)
            unique_facts.append(f)

    # Cap at 8 facts to keep summary short
    summary = ". ".join(unique_facts[:8])

    # Save summary to conversation
    conv_result = await db.execute(
        select(Conversation).filter(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalars().first()
    if conversation:
        conversation.summary = summary
        conversation.summary_message_count = message_count
        await db.commit()


def _sanitize_message_sequence(messages: list[AnyMessage]) -> list[AnyMessage]:
    sanitized: list[AnyMessage] = []

    i = 0
    while i < len(messages):
        msg = messages[i]

        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            expected_ids = {tc.get("id") for tc in msg.tool_calls if tc.get("id")}

            tool_msgs = []
            j = i + 1
            while j < len(messages) and isinstance(messages[j], ToolMessage):
                tool_msgs.append(messages[j])
                j += 1

            found_ids = {getattr(tm, "tool_call_id", None) for tm in tool_msgs}

            if expected_ids and expected_ids.issubset(found_ids):
                sanitized.append(msg)
                for tm in tool_msgs:
                    if getattr(tm, "tool_call_id", None) in expected_ids:
                        sanitized.append(tm)
                i = j
            else:
                i = j

        elif isinstance(msg, ToolMessage):
            i += 1

        else:
            sanitized.append(msg)
            i += 1

    return sanitized


def _extract_text_content(content) -> str:
    """Extract plain text from message content.
    Claude returns content as a list of blocks (text, tool_use, etc.).
    OpenAI returns content as a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        return " ".join(text_parts)
    return str(content) if content else ""


async def save_agent_messages(
    db: AsyncSession,
    conversation_id: str,
    messages: list[AnyMessage],
) -> None:
    for msg in messages:
        msg_type_name = type(msg).__name__

        if msg_type_name == "AIMessage":
            tool_calls = getattr(msg, "tool_calls", None)

            if tool_calls:
                serializable_calls = []
                for tc in tool_calls:
                    serializable_calls.append({
                        "id": tc.get("id", str(uuid_mod.uuid4())),
                        "name": tc.get("name", ""),
                        "args": tc.get("args", {}),
                    })

                db_msg = Message(
                    conversation_id=conversation_id,
                    sender_type=MessageSenderType.AI.value,
                    direction=MessageDirection.OUTBOUND.value,
                    message_type=MessageType.TOOL_CALL.value,
                    content=_extract_text_content(msg.content),
                    tool_metadata=serializable_calls,
                    status=MessageStatus.SENT.value,
                )
                db.add(db_msg)

            else:
                db_msg = Message(
                    conversation_id=conversation_id,
                    sender_type=MessageSenderType.AI.value,
                    direction=MessageDirection.OUTBOUND.value,
                    message_type=MessageType.TEXT.value,
                    content=_extract_text_content(msg.content),
                    status=MessageStatus.SENT.value,
                )
                db.add(db_msg)

        elif msg_type_name == "ToolMessage":
            db_msg = Message(
                conversation_id=conversation_id,
                sender_type=MessageSenderType.TOOL.value,
                direction=MessageDirection.OUTBOUND.value,
                message_type=MessageType.TOOL_RESULT.value,
                content=_extract_text_content(msg.content),
                tool_metadata={
                    "tool_call_id": getattr(msg, "tool_call_id", ""),
                    "tool_name": getattr(msg, "name", ""),
                },
                status=MessageStatus.SENT.value,
            )
            db.add(db_msg)

    await db.commit()
