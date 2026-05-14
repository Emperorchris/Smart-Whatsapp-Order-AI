from ..graph.agent_state import AgentState
from sqlalchemy.orm import Session
from langchain_core.messages import AIMessage, HumanMessage
from ...core.config import Config
from langchain_openai import ChatOpenAI
from ...services import human_handoff_service, conversation_service
from ...db.schemas import human_hand_off_schema
from ...core.utils import HandOffStatus, HandOffTriggeredBy
from ...db.model import human_hand_off_model


def handoff_node(state: AgentState, db: Session) -> AgentState:
    latest_message = state["messages"][-1].content if state["messages"] else ""
    conversation_id = state["conversation_id"]
    customer_id = state["customer_id"]

    handoff_data = human_hand_off_schema.HumanHandOffSchema(
        conversation_id=conversation_id,
        triggered_by=HandOffTriggeredBy.CUSTOMER.value,
        reason=state["handoff_reason"] if "handoff_reason" in state else "AI could not handle the request",
        assigned_staff_id=None,
        status=HandOffStatus.REQUESTED.value
    )
    human_handoff_service.create_handoff(db, handoff_data)
    
    
    
    conversation_service.disable_ai(db, conversation_id)

    reply = (
        "I'm connecting you with a human agent right now. "
        "Please hold on — someone will be with you shortly."
    )
    
    return {
        "messages": [AIMessage(content=reply)],
        "handoff_active": True
    }
