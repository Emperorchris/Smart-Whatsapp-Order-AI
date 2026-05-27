from loguru import logger
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
# from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from .agent_state import AgentState
from ..tools.product_tools import product_tools
from ..tools.cart_tools import cart_tools
from ..tools.order_tools import order_tools
from ..tools.handoff_tools import handoff_tools
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

all_tools = product_tools + cart_tools + order_tools + handoff_tools + address_tools + order_item_tools

# llm = ChatOpenAI(model=Config.OPENAI_LLM_MODEL, temperature=0)
llm = ChatAnthropic(model=Config.ANTHROPIC_LLM_MODEL, temperature=0)
llm_with_tools = llm.bind_tools(all_tools)


async def agent_node(state: AgentState):
    messages = state["messages"]

    # Prepend system prompt with customer context
    raw_name = state.get("customer_display_name") or state.get("customer_name") or ""
    # Extract a usable first name — take the last word if it looks like "Business by Name"
    customer_name = raw_name
    if any(keyword in raw_name.lower() for keyword in ["by", "with"]):
        customer_name = raw_name.split(" by ")[-1].strip()
    elif " " in raw_name:
        customer_name = raw_name.split()[0].strip()

    logger.info("agent_node: raw_name={!r}, customer_name={!r}", raw_name, customer_name)

    if customer_name:
        name_instruction = (
            f"- Name: *{customer_name}*\n"
            f"- Use their name ONLY in the first greeting and when saying goodbye. Do NOT use their name in every message, it sounds robotic."
        )
    else:
        name_instruction = "- Name: unknown"

    sender_type = state.get("sender_type", "customer")
    base_prompt = STAFF_PROMPT if sender_type == utils.MessageSenderType.STAFF.value else CUSTOMER_PROMPT
    personalized_prompt = base_prompt + f"\n\n## Current user\n{name_instruction}"

    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=personalized_prompt)] + messages
    else:
        messages = [SystemMessage(content=personalized_prompt)] + messages[1:]

    response = await llm_with_tools.ainvoke(messages)

    tool_calls = getattr(response, "tool_calls", None)
    if tool_calls:
        logger.info("agent_node: LLM called tools — {}", [tc.get("name") for tc in tool_calls])
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
graph_builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph_builder.add_edge("tools", "agent")  # after tool execution, go back to agent

graph = graph_builder.compile()


async def run_agent(state: AgentState, db: AsyncSession, customer_id: str = None, conversation_id: str = None) -> dict:
    """Invoke the agent graph with a database session and customer context."""
    config = {
        "configurable": {
            "db": db,
            "customer_id": customer_id or state.get("customer_id"),
            "conversation_id": conversation_id or state.get("conversation_id"),
            "customer_whatsapp_number": state.get("customer_whatsapp_number"),
        }
    }
    return await graph.ainvoke(state, config=config)
