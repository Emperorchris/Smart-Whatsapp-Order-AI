from langchain_core.messages import AIMessage
from sqlalchemy.orm import Session
from ..graph.agent_state import AgentState
from ...services import customer_service
from ...db.schemas.customers_schema import CustomerSchema


def customer_identifier_node(state: AgentState, db: Session) -> dict:
    whatsapp_number = state["customer_whatsapp_number"]

    # Try to find existing customer
    try:
        customer = customer_service.get_customer_by_whatsapp_number(db, whatsapp_number)
    except Exception:
        # New customer — create a record with just their WhatsApp number
        customer = customer_service.create_customer(
            db,
            CustomerSchema(
                whatsapp_number=whatsapp_number,
            )
        )

    return {
        "customer_id": str(customer.id),
    }
