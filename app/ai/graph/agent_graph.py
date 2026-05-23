from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from .agent_state import AgentState
from ..tools.product_tools import product_tools
from ..tools.cart_tools import cart_tools
from ..tools.order_tools import order_tools
from ..tools.handoff_tools import handoff_tools
from ..prompts.system_prompt import SYSTEM_PROMPT
from ...core.config import Config


# from ..nodes import (
#     product_lookup_node,
#     handoff_node,
#     customer_node,
#     cart_node,
#     router_node,
#     order_node,
# )
# from ...core.utils import GraphNodeName

all_tools = product_tools + cart_tools + order_tools + handoff_tools

llm = ChatOpenAI(model=Config.OPENAI_LLM_MODEL, temperature=0)
llm_with_tools = llm.bind_tools(all_tools)


async def agent_node(state: AgentState):
    messages = state["messages"]

    # Prepend system prompt if not already there
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    response = await llm_with_tools.ainvoke(messages)
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
        }
    }
    return await graph.ainvoke(state, config=config)
