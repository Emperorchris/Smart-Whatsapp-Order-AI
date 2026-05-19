from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ...core.config import Config
from pydantic import BaseModel
from ..graph.agent_state import AgentState
from sqlalchemy.orm import Session


class IntentClassification(BaseModel):
    intent: str
    handoff_reason: str | None = None


llm = ChatOpenAI(model=Config.OPENAI_LLM_MODEL, temperature=0)
structured_llm = llm.with_structured_output(IntentClassification)


def router_node(state: AgentState) -> dict:
    latest_message = state["messages"][-1].content if state["messages"] else ""

    result: IntentClassification = structured_llm.invoke([
        SystemMessage(content=""" 
           You are a WhatsApp commerce assistant router.
            Classify the customer message into exactly one of these intents:

            - product_inquiry: customer is asking about products, prices, availability, variants, sizes, colors
            - cart: customer wants to add, remove, view or clear their cart
            - order: customer wants to place an order or check order status
            - handoff: customer is frustrated, requesting a human, or has a complex issue the AI cannot handle
            - chitchat: greetings, thank you, off-topic or general conversation
            - identify_customer: message contains information that can help identify the customer (e.g. WhatsApp number, name, email, order details)
            
            
            If the intent is handoff, also provide a brief handoff_reason.
            
           if the message is unclear or could fit multiple intents, choose the most likely intent based on the message content, if there is no clear intent, choose handoff.
        """),
        HumanMessage(content=latest_message)
    ])
    
    state["intent"] = result.intent
    if result.handoff_reason:
        state["handoff_reason"] = result.handoff_reason
    
    return {
        "intent": result.intent,
        "handoff_reason": result.handoff_reason
    }
