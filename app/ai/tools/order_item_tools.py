from loguru import logger
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...services import order_service, order_item_service


@tool
async def get_order_items(config: RunnableConfig, order_number: str) -> str:
    """Get the detailed item breakdown for a specific order.
    Use this when a customer asks to see what items are in their order,
    or wants to see the full details of an order."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    logger.info("get_order_items called — order_number={!r}, customer_id={}", order_number, customer_id)

    try:
        order = await order_service.get_order_by_order_number(db, order_number)
        logger.info("get_order_items: found order id={} status={}", order.id, order.status)
    except Exception as exc:
        logger.error("get_order_items: order lookup failed — {}", exc)
        return f"No order found with number {order_number}."

    if str(order.customer_id) != customer_id:
        return f"No order found with number {order_number} in your account."

    try:
        items = await order_item_service.get_order_items_by_order_id(db, str(order.id))
        logger.info("get_order_items: found {} items", len(items))
    except Exception as exc:
        logger.error("get_order_items: FAILED to fetch items — {}", exc)
        return f"Sorry, I couldn't retrieve the items for order {order_number}. Please try again."

    if not items:
        return f"Order *{order_number}* has no items."

    item_lines = []
    for item in items:
        name = item.product_name or "Unknown product"
        if item.product_variant_attributes:
            attrs = ", ".join(f"{k}: {v}" for k, v in item.product_variant_attributes.items())
            name += f" ({attrs})"
        item_lines.append(f"• {item.quantity} unit(s) of {name} @ NGN {item.unit_price:,.2f}")

    result = (
        f"Order *{order.order_number}*\n\n"
        f"Status: *{order.status}*\n"
        f"Payment: *{order.payment_status}*\n\n"
        f"Items:\n" + "\n".join(item_lines) + "\n\n"
        f"Total: *NGN {order.total_amount:,.2f}*"
    )

    if order.address_line:
        delivery = f"{order.address_line}, {order.address_city}, {order.address_state}"
        if order.address_landmark:
            delivery += f" (Landmark: {order.address_landmark})"
        result += f"\n\nDelivery Address: {delivery}"

    return result


order_item_tools = [get_order_items]
