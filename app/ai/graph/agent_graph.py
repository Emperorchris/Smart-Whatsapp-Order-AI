from loguru import logger
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

# from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from .agent_state import AgentState
from ..tools.product_tools import product_tools
from ..tools.cart_tools import cart_tools
from ..tools.order_tools import order_tools
from ..tools.handoff_tools import (
    customer_handoff_tools,
    staff_handoff_tools,
    handoff_tools,
)
from ..tools.address_tools import address_tools
from ..tools.order_item_tools import order_item_tools

# from ..prompts.system_prompt import SYSTEM_PROMPT
from ..prompts.customers_prompt import CUSTOMER_PROMPT
from ..prompts.staff_prompt import STAFF_PROMPT
from ...core.config import Config
from ...core import utils


# from ..nodes import (
#     product_lookup_node,
#     handoff_node,
#     customer_node,
#     cart_node,
#     router_node,
#     order_node,
# )
# from ...core.utils import GraphNodeName


all_tools = (
    product_tools
    + cart_tools
    + order_tools
    + address_tools
    + order_item_tools
    + handoff_tools
)

staff_tools = (
    product_tools
    + cart_tools
    + order_tools
    + address_tools
    + order_item_tools
    + staff_handoff_tools
    + customer_handoff_tools
)

_CUSTOMER_ALL_TOOLS = (
    product_tools
    + cart_tools
    + order_tools
    + address_tools
    + order_item_tools
    + customer_handoff_tools
)


llm = ChatOpenAI(model=Config.OPENAI_LLM_MODEL, temperature=0)
# llm = ChatAnthropic(model=Config.ANTHROPIC_LLM_MODEL, temperature=0)


async def agent_node(state: AgentState):
    messages = state["messages"]

    # Resolve user name
    raw_name = state.get("customer_display_name") or state.get("customer_name") or ""
    customer_name = raw_name
    if any(keyword in raw_name.lower() for keyword in ["by", "with"]):
        customer_name = raw_name.split(" by ")[-1].strip()
    elif " " in raw_name:
        customer_name = raw_name.split()[0].strip()

    sender_type = state.get("sender_type", utils.MessageSenderType.CUSTOMER.value)
    if sender_type == utils.MessageSenderType.STAFF.value:
        customer_name = raw_name or "Administrator"

    logger.info(
        "agent_node: raw_name={!r}, customer_name={!r}", raw_name, customer_name
    )

    # Static system prompt with cache_control for Anthropic prompt caching.
    # The system prompt is identical for all users of the same type, so Anthropic
    # caches it and charges 1/10th for cached input tokens on subsequent requests.
    base_prompt = (
        STAFF_PROMPT
        if sender_type == utils.MessageSenderType.STAFF.value
        else CUSTOMER_PROMPT
    )

    cached_system = SystemMessage(
        content=[
            {
                "type": "text",
                "text": base_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    )

    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [cached_system] + messages
    else:
        messages = [cached_system] + messages[1:]

    # Inject personalization into the first HumanMessage (not system prompt)
    name_context = (
        f"[Current user: {customer_name}. Use their name ONLY in the first greeting and goodbye.]"
        if customer_name
        else ""
    )
    if name_context:
        for i, msg in enumerate(messages):
            if isinstance(msg, HumanMessage):
                messages[i] = HumanMessage(content=f"{name_context}\n{msg.content}")
                break

    # Staff gets staff tools, customers get all customer tools — LLM decides what to call
    if sender_type == utils.MessageSenderType.STAFF.value:
        tools = staff_tools
    else:
        tools = _CUSTOMER_ALL_TOOLS
        logger.info("agent_node: tools_count={}", len(tools))

    response = await llm.bind_tools(tools).ainvoke(messages)

    tool_calls = getattr(response, "tool_calls", None)
    if tool_calls:
        logger.info(
            "agent_node: LLM called tools — {}", [tc.get("name") for tc in tool_calls]
        )
    else:
        content = response.content
        preview = str(content)[:200] if content else "(empty)"
        logger.info("agent_node: LLM responded with text — {}", preview)

    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


graph_builder = StateGraph(AgentState)

graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", ToolNode(all_tools))

graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges(
    "agent", should_continue, {"tools": "tools", END: END}
)
graph_builder.add_edge("tools", "agent")  # after tool execution, go back to agent

graph = graph_builder.compile()


async def run_agent(
    state: AgentState,
    db: AsyncSession,
    customer_id: str = None,
    conversation_id: str = None,
    staff_id: str = None,
) -> dict:
    """Invoke the agent graph with a database session and customer/staff context."""
    config = {
        "configurable": {
            "db": db,
            "customer_id": customer_id or state.get("customer_id"),
            "conversation_id": conversation_id or state.get("conversation_id"),
            "customer_whatsapp_number": state.get("customer_whatsapp_number"),
            "staff_id": staff_id or state.get("staff_id"),
        }
    }
    return await graph.ainvoke(state, config=config, recursion_limit=10)
