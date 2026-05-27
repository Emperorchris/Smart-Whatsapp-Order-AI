import uuid as uuid_mod
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    AnyMessage,
)
from ...db.model.message_model import Message
from ...core.utils import (
    MessageDirection,
    MessageSenderType,
    MessageStatus,
    MessageType,
)


MAX_HISTORY = 30


async def load_conversation_history(
    db: AsyncSession, conversation_id: str
) -> list[AnyMessage]:
    result = await db.execute(
        select(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    rows = list(result.scalars().all())

    rows = rows[-MAX_HISTORY:]

    messages: list[AnyMessage] = []
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
                    # content=msg.content or "",  # OpenAI returns str
                    content=_extract_text_content(msg.content),  # Claude returns list of blocks
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
                    # content=msg.content or "",  # OpenAI returns str
                    content=_extract_text_content(msg.content),  # Claude returns list of blocks
                    status=MessageStatus.SENT.value,
                )
                db.add(db_msg)

        elif msg_type_name == "ToolMessage":
            db_msg = Message(
                conversation_id=conversation_id,
                sender_type=MessageSenderType.TOOL.value,
                direction=MessageDirection.OUTBOUND.value,
                message_type=MessageType.TOOL_RESULT.value,
                content=_extract_text_content(msg.content),  # safe for both OpenAI and Claude
                tool_metadata={
                    "tool_call_id": getattr(msg, "tool_call_id", ""),
                    "tool_name": getattr(msg, "name", ""),
                },
                status=MessageStatus.SENT.value,
            )
            db.add(db_msg)

    await db.commit()
