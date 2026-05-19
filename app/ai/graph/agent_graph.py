from langgraph.graph import StateGraph, START, END
from .agent_state import AgentState
from ..nodes import (
    product_lookup_node,
    handoff_node,
    customer_node,
    cart_node,
    router_node
)

from ...core.utils import GraphNodeName

def route_by_intent(state: AgentState) -> str:
    return state["intent"]  # router node writes this, function just reads it


graph_builder = StateGraph(AgentState)

graph_builder.add_node(GraphNodeName.CUSTOMER_NODE.value, customer_node.customer_identifier_node)
graph_builder.add_node(GraphNodeName.CART_NODE.value, cart_node.cart_node)
graph_builder.add_node(GraphNodeName.PRODUCT_LOOKUP_NODE.value, product_lookup_node.product_lookup_node)
graph_builder.add_node(GraphNodeName.HANDOFF_NODE.value, handoff_node.handoff_node)
graph_builder.add_node(GraphNodeName.ROUTER_NODE.value, router_node.router_node)



graph_builder.add_edge(START, GraphNodeName.CUSTOMER_NODE.value)
graph_builder.add_edge(GraphNodeName.CUSTOMER_NODE.value, GraphNodeName.ROUTER_NODE.value)


graph_builder.add_conditional_edges(
    GraphNodeName.ROUTER_NODE.value,
    route_by_intent,
    {
        "product_inquiry": GraphNodeName.PRODUCT_LOOKUP_NODE.value,
        "handoff": GraphNodeName.HANDOFF_NODE.value,
        "cart": GraphNodeName.CART_NODE.value
    }
)


graph_builder.add_edge(GraphNodeName.PRODUCT_LOOKUP_NODE.value, END)
graph_builder.add_edge(GraphNodeName.CART_NODE.value, END)
graph_builder.add_edge(GraphNodeName.HANDOFF_NODE.value, END)


graph = graph_builder.compile()