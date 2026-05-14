from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Optional

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    conversation_id: Optional[str]
    customer_id: Optional[str]
    customer_whatsapp_number: str
    intent: Optional[str] #product_inquiry, order_status, return_request, etc.
    sentiment: Optional[str] #positive, negative, neutral
    cart_id: Optional[str]
    order_id: Optional[str]
    payment_status: Optional[str] #paid, pending, failed
    search_results: Optional[list] #for product inquiries, etc.
    handoff_active: bool = False
    handoff_reason: Optional[str] #if handoff is triggered, the reason for it
    response: Optional[str]