from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...services import human_handoff_service, conversation_service, whatsapp_service
from ...db.schemas import human_hand_off_schema
from ...core.utils import HandOffStatus, HandOffTriggeredBy


@tool
async def request_human_agent(config: RunnableConfig, reason: str = "Customer requested a human agent") -> str:
    """Transfer the customer to a human agent.
    Use this when:
    - The customer explicitly asks to speak to a human
    - The customer is frustrated or upset
    - You cannot handle their request
    - The issue requires human judgement (refunds, complaints, etc.)"""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]
    conversation_id = config["configurable"]["conversation_id"]

    handoff_data = human_hand_off_schema.HumanHandOffSchema(
        conversation_id=conversation_id,
        triggered_by=HandOffTriggeredBy.CUSTOMER.value,
        reason=reason,
        assigned_staff_id=None,
        status=HandOffStatus.PENDING.value,
    )

    await human_handoff_service.create_handoff(db, handoff_data)
    await conversation_service.start_handoff(db, conversation_id, reason=reason)

    await whatsapp_service.notify_all_staff(
        db=db,
        message=f"Customer {customer_id} has been transferred to a human agent. Reason: {reason}",
        customer_id=customer_id,
    )

    return "Customer has been connected to a human agent. Staff have been notified."


handoff_tools = [request_human_agent]
