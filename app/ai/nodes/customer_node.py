from langchain_core.runnables import RunnableConfig
from ..graph.agent_state import AgentState
from ...services import customer_service
from ...db.schemas.customers_schema import CustomerSchema


def customer_identifier_node(state: AgentState, config: RunnableConfig) -> dict:
    db = config["configurable"]["db"]
    whatsapp_number = state["customer_whatsapp_number"]

    # Try to find existing customer
    try:
        customer = customer_service.get_customer_by_whatsapp_number(db, whatsapp_number)
    except Exception:
        # New customer — create a record with just their WhatsApp number
        # Prefer profile name / display name from state, fall back to the phone number
        name = state.get("customer_name") or state.get("customer_display_name")
        display_name = state.get("customer_display_name") or name
        email = state.get("customer_email")
        extra = state.get("customer_extra_metadata")

        customer = customer_service.create_customer(
            db,
            CustomerSchema(
                name=name,
                whatsapp_number=whatsapp_number,
                display_name=display_name,
                email=email,
                extra_metadata=extra,
            )
        )

    return {
        "customer_id": str(customer.id),
    }
