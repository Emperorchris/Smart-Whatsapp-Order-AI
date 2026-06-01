from loguru import logger
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...services import order_service, order_item_service


def _first_image_url(product_media: list[dict] | None) -> str | None:
    """Return the first image URL from a product_media JSON list."""
    if not product_media:
        return None
    for media in product_media:
        if media.get("type") in ("image", "live_image"):
            return media.get("url")
    # fallback: first video if no image
    if product_media:
        return product_media[0].get("url")
    return None


@tool
async def get_order_items(config: RunnableConfig, order_number: str) -> str:
    """Get the detailed item breakdown for a specific order, shown as product cards with images.
    Use this when a customer asks to see what items are in their order,
    or wants to see the full details of an order."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    logger.info(
        "get_order_items called — order_number={!r}, customer_id={}",
        order_number,
        customer_id,
    )

    try:
        order = await order_service.get_order_by_order_number(db, order_number)
        logger.info(
            "get_order_items: found order id={} status={}", order.id, order.status
        )
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

    # Build order header block
    header = (
        f"*Order {order.order_number}*\n"
        f"Status: {order.status}  |  Payment: {order.payment_status}\n"
        f"*Total: NGN {order.total_amount:,.2f}*"
    )
    if order.address_line:
        delivery = f"{order.address_line}, {order.address_city}, {order.address_state}"
        if order.address_landmark:
            delivery += f" (Landmark: {order.address_landmark})"
        header += f"\nDelivery: {delivery}"

    # Build one product block per item with image
    product_blocks = []
    for item in items:
        name = item.product_name or "Unknown product"
        if item.product_variant_attributes:
            attrs = ", ".join(
                f"{k}: {v}" for k, v in item.product_variant_attributes.items()
            )
            name += f" ({attrs})"

        caption = (
            f"*{name}*\n"
            f"• Qty: {item.quantity} unit(s)\n"
            f"• Unit Price: NGN {item.unit_price:,.2f}\n"
            f"• Subtotal: NGN {item.subtotal:,.2f}"
        )

        img_url = _first_image_url(item.product_media)
        media_tag = f"\n[PRODUCT_MEDIA]{img_url}[/PRODUCT_MEDIA]" if img_url else ""

        product_blocks.append(f"[PRODUCT_START]\n{caption}{media_tag}\n[PRODUCT_END]")

    result = f"[PRODUCT_START]\n{header}\n[PRODUCT_END]\n\n" + "\n\n".join(
        product_blocks
    )
    return result


@tool
async def get_order_items_media(config: RunnableConfig, order_number: str) -> str:
    """Get all media (images/videos) for items in a specific order.
    Use this ONLY when a customer wants to see more photos or videos of an item they already ordered.
    This is different from get_product_images — use this when the context is about an order, not product browsing.
    For example: customer replies to an order item card saying 'show more images', 'send pictures', 'more photos of this'."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    try:
        order = await order_service.get_order_by_order_number(db, order_number)
    except Exception:
        return f"No order found with number {order_number}."

    if str(order.customer_id) != customer_id:
        return f"No order found with number {order_number} in your account."

    try:
        items = await order_item_service.get_order_items_by_order_id(db, str(order.id))
    except Exception as exc:
        logger.error("get_order_items_media: FAILED — {}", exc)
        return f"Sorry, I couldn't retrieve media for order {order_number}."

    if not items:
        return f"Order *{order_number}* has no items."

    blocks = []
    for item in items:
        media_list = item.product_media or []
        all_urls = [m.get("url") for m in media_list if m.get("url")]
        if not all_urls:
            continue

        name = item.product_name or "Unknown product"
        if item.product_variant_attributes:
            attrs = ", ".join(
                f"{k}: {v}" for k, v in item.product_variant_attributes.items()
            )
            name += f" ({attrs})"

        media_csv = ",".join(all_urls)
        blocks.append(
            f"[PRODUCT_START]\n*{name}*\n[PRODUCT_MEDIA]{media_csv}[/PRODUCT_MEDIA]\n[PRODUCT_END]"
        )

    if not blocks:
        return f"No media found for items in order *{order_number}*."

    return "\n\n".join(blocks)


order_item_tools = [get_order_items, get_order_items_media]
