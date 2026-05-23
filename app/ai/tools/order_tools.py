from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...services import order_service, product_service, cart_service, customer_service, order_item_service
from ...services.product_variant_service import get_variant_by_id
from ...db.schemas import order_schema, order_item_schema
from ...db.model import product_variant_model
from ...core import utils, common


@tool
async def place_order(config: RunnableConfig, delivery_address: str = "No address provided") -> str:
    """Place an order from the customer's current cart.
    Use this when a customer wants to checkout or place an order.
    Requires a delivery address if the customer provides one."""

    db: AsyncSession = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    try:
        cart = await cart_service.get_cart_by_customer_id(db, customer_id)
    except Exception:
        return "You don't have any items in your cart. Please add products before placing an order."

    cart_items = cart.cart_items
    if not cart_items:
        return "Your cart is empty. Please add products before placing an order."

    stock_issues = []
    for item in cart_items:
        if item.variant_id:
            try:
                variant = await get_variant_by_id(db, str(item.variant_id))
                if variant.inventory_quantity < item.quantity:
                    try:
                        product = await product_service.get_product_by_id(db, str(item.product_id))
                        name = product.name
                    except Exception:
                        name = "a product"
                    attrs = ", ".join(f"{k}: {val}" for k, val in variant.attributes.items())
                    if variant.inventory_quantity == 0:
                        stock_issues.append(f"*{name}* ({attrs}) is out of stock")
                    else:
                        stock_issues.append(
                            f"*{name}* ({attrs}) only has {variant.inventory_quantity} in stock (you requested {item.quantity})"
                        )
            except Exception:
                pass

    if stock_issues:
        return (
            "Some items in your cart have stock issues:\n\n"
            + "\n".join(f"• {issue}" for issue in stock_issues)
            + "\n\nPlease update your cart and try again."
        )

    try:
        customer = await customer_service.get_customer_by_id(db, customer_id)
        order_number = common.generate_order_number()
        total_amount = sum(item.subtotal for item in cart_items)

        order_data = order_schema.OrderSchema(
            customer_id=customer_id,
            customer_name=customer.display_name,
            customer_whatsapp_number=customer.whatsapp_number,
            order_number=order_number,
            total_amount=total_amount,
            delivery_address=delivery_address,
        )

        order = await order_service.create_order(db, order_data)

        for item in cart_items:
            try:
                product = await product_service.get_product_by_id(db, str(item.product_id))
            except Exception:
                continue

            variant_attrs = None
            if item.variant_id:
                try:
                    variant = await get_variant_by_id(db, str(item.variant_id))
                    variant_attrs = variant.attributes
                except Exception:
                    pass

            order_item_data = order_item_schema.OrderItemSchema(
                order_id=order.id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                product_name=product.name,
                product_sku=product.sku,
                product_description=product.description,
                product_category=None,
                product_media=[m.model_dump() for m in product.media] if product.media else None,
                product_variant_attributes=variant_attrs,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            await order_item_service.create_order_item(db, order_item_data)

            if item.variant_id:
                variant_result = await db.execute(
                    select(product_variant_model.ProductVariant).filter(
                        product_variant_model.ProductVariant.id == item.variant_id
                    )
                )
                variant_record = variant_result.scalars().first()
                if variant_record:
                    variant_record.inventory_quantity = max(
                        0, variant_record.inventory_quantity - item.quantity
                    )

        await db.commit()
        await cart_service.delete_cart(db, cart.id)

        return (
            f"Order placed successfully!\n\n"
            f"• Order Number: *{order_number}*\n"
            f"• Total: *NGN {total_amount:,.2f}*\n"
            f"• Delivery Address: {delivery_address}\n\n"
            f"You can check your order status anytime."
        )
    except Exception as e:
        await db.rollback()
        return f"Sorry, there was an error placing your order: {str(e)}"


@tool
async def check_order_status(config: RunnableConfig, order_number: str = None) -> str:
    """Check the status of customer's orders.
    If an order number is provided, shows that specific order.
    Otherwise shows all orders for the customer."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    if order_number:
        try:
            order = await order_service.get_order_by_order_number(db, order_number)
            if str(order.customer_id) != customer_id:
                return f"No order found with number {order_number} in your account."
            return (
                f"Order *{order.order_number}*\n\n"
                f"• Status: *{order.status}*\n"
                f"• Total: *NGN {order.total_amount:,.2f}*"
            )
        except Exception:
            return f"No order found with number {order_number}."

    orders = await order_service.get_orders_by_customer_id(db, customer_id)
    if not orders:
        return "You don't have any orders yet."

    lines = []
    for o in orders:
        lines.append(
            f"• Order *{o.order_number}*\n"
            f"  Status: *{o.status}*\n"
            f"  Total: *NGN {o.total_amount:,.2f}*"
        )
    return "Here are your orders:\n\n" + "\n\n".join(lines)


@tool
async def cancel_order(config: RunnableConfig, order_number: str) -> str:
    """Cancel a pending order by order number.
    Only orders with 'pending' status can be cancelled."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    try:
        order = await order_service.get_order_by_order_number(db, order_number)
    except Exception:
        return f"No order found with number {order_number}."

    if str(order.customer_id) != customer_id:
        return f"No order found with number {order_number} in your account."

    if order.status != utils.OrderStatus.PENDING.value:
        return f"Only pending orders can be cancelled. Order {order_number} is currently *{order.status}*."

    await order_service.cancel_order(db, order.id)
    return f"Order {order_number} has been cancelled successfully."


order_tools = [place_order, check_order_status, cancel_order]
