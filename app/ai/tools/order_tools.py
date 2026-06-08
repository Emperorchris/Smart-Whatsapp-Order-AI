from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...db.model.order_model import Order
from ...db.model.customer_model import Customer as CustomerModel
from ...services import (
    order_service,
    product_service,
    cart_service,
    customer_service,
    order_item_service,
    customer_address_service,
    whatsapp_service,
    bank_account_service,
    websocket_service,
)
from ...services.product_variant_service import get_variant_by_id
from ...db.schemas import order_schema, order_item_schema, customer_address_schema
from ...db.model import product_variant_model
from ...core import utils, common


@tool
async def place_order(
    config: RunnableConfig,
    customer_address_id: str = None,
) -> str:
    """Place an order from the customer's current cart.
    Use this when a customer wants to checkout or place an order.
    Call this with NO parameters first — the system will send interactive buttons for the customer to pick a saved address or add a new one.
    Only pass customer_address_id AFTER the customer has selected an address via the interactive buttons."""

    db: AsyncSession = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    try:
        customer = await customer_service.get_customer_by_id(db, customer_id)
    except Exception:
        return "Customer not found"

    # First-time order: ask for full name if not yet confirmed
    existing_orders = await order_service.get_orders_by_customer_id(db, customer_id)
    metadata = customer.extra_metadata or {}
    if not existing_orders and not metadata.get("name_confirmed"):
        return (
            "Since this is your first order, I need your full name for delivery. "
            "Please send me your full name."
        )

    try:
        cart = await cart_service.get_cart_by_customer_id(db, customer_id)
    except Exception:
        return "You don't have any items in your cart. Please add products before placing an order."

    cart_items = cart.cart_items
    if not cart_items:
        return "Your cart is empty. Please add products before placing an order."

    # Resolve delivery address
    address: customer_address_schema.CustomerAddressResponse | None = None
    customer_phone = config["configurable"].get("customer_whatsapp_number", "")

    if customer_address_id:
        try:
            address = await customer_address_service.get_address_by_id(
                db, customer_address_id
            )
            if str(address.customer_id) != str(customer_id):
                return "That address was not found. Please provide a valid address."
        except Exception:
            return "That address was not found. Please provide a valid address."
    else:
        # No address provided — always show address selection
        addresses = await customer_address_service.get_addresses_by_customer_id(
            db, customer_id
        )
        logger.info(
            "place_order: phone={!r}, saved_addresses={}",
            customer_phone,
            len(addresses) if addresses else 0,
        )
        if addresses and customer_phone:
            # Send saved addresses as interactive buttons
            rows = []
            for addr in addresses:
                default_tag = " (default)" if addr.is_default else ""
                rows.append(
                    {
                        "id": f"addr_select_{addr.id}",
                        "title": f"{addr.label.capitalize()}{default_tag}",
                        "description": f"{addr.address_line}, {addr.city}",
                    }
                )
            rows.append(
                {
                    "id": "addr_select_new",
                    "title": "Add new address",
                    "description": "Enter a new delivery address",
                }
            )
            sent = False
            try:
                await whatsapp_service.send_interactive_list(
                    to=customer_phone,
                    body="Pick a delivery address for your order:",
                    button_text="Select address",
                    sections=[{"title": "Saved Addresses", "rows": rows}],
                    header="Delivery Address",
                )
                sent = True
                logger.info("place_order: saved address list sent successfully")
            except Exception as exc:
                logger.error("place_order: FAILED to send address list — {}", exc)

            if sent:
                return (
                    "[INTERACTIVE_SENT] Saved address list sent to customer. "
                    "Do NOT send any additional text. Wait silently for their selection."
                )
            # Fall through if send failed — ask manually
        elif addresses:
            lines = []
            for i, addr in enumerate(addresses, 1):
                default_tag = " *(default)*" if addr.is_default else ""
                lines.append(
                    f"{i}. *{addr.label.capitalize()}*{default_tag} — {addr.address_line}, {addr.city}"
                )
            return (
                "You need a delivery address to place your order. You have these saved addresses:\n\n"
                + "\n".join(lines)
                + "\n\nWhich one should I use? Or you can add a new address."
            )

        # No saved addresses — send interactive list to collect address type
        logger.info("place_order: no saved addresses, customer_phone={!r}", customer_phone)
        if customer_phone:
            labels = [member for member in utils.AddressLabel]
            sections = [
                {
                    "title": "Address Type",
                    "rows": [
                        {
                            "id": f"addr_label_{label.value}",
                            "title": label.value.capitalize(),
                        }
                        for label in labels
                    ],
                }
            ]
            sent = False
            try:
                await whatsapp_service.send_interactive_list(
                    to=customer_phone,
                    body="To place your order I need your delivery address. What type of address is it?",
                    button_text="Select type",
                    sections=sections,
                    header="Delivery Address",
                    footer="Step 1 of 2",
                )
                sent = True
                logger.info("place_order: address type picker sent successfully")
            except Exception as exc:
                logger.error("place_order: FAILED to send address type picker — {}", exc)

            if sent:
                return (
                    "[INTERACTIVE_SENT] Address type picker sent to customer. "
                    "Do NOT send any additional text. Wait silently for their selection."
                )
            # Fall through to text prompt if send failed
        return (
            "You don't have a saved delivery address yet. "
            "Please tell me your address details: street address, city, state, and a nearby landmark."
        )

    # Validate quantities and check stock
    invalid_items = [i for i in cart_items if not i.quantity or i.quantity < 1]
    if invalid_items:
        return "Some items in your cart have invalid quantities. Please update your cart and try again."

    stock_issues = []
    for item in cart_items:
        if item.variant_id:
            try:
                variant = await get_variant_by_id(db, str(item.variant_id))
                if variant.inventory_quantity < item.quantity:
                    try:
                        product = await product_service.get_product_by_id(
                            db, str(item.product_id)
                        )
                        name = product.name
                    except Exception:
                        name = "a product"
                    attrs = ", ".join(
                        f"{k}: {val}" for k, val in variant.attributes.items()
                    )
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
        order_number = "#ORD-" + common.generate_order_number()
        total_amount = sum(item.subtotal for item in cart_items)

        order_data = order_schema.OrderSchema(
            customer_id=customer_id,
            customer_name=customer.display_name,
            customer_whatsapp_number=customer.whatsapp_number,
            order_number=order_number,
            total_amount=total_amount,
            address_label=address.label,
            address_full_name=address.full_name,
            address_phone_number=address.phone_number,
            address_line=address.address_line,
            address_city=address.city,
            address_state=address.state,
            address_country=address.country,
            address_postal_code=address.postal_code,
            address_landmark=address.landmark,
        )

        order = await order_service.create_order(db, order_data)

        for item in cart_items:
            try:
                product = await product_service.get_product_by_id(
                    db, str(item.product_id)
                )
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
                product_media=[m.model_dump() for m in product.media]
                if product.media
                else None,
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
                    # Broadcast low stock alert if variant hits threshold
                    threshold = variant_record.low_stock_threshold or 5
                    if variant_record.inventory_quantity <= threshold:
                        try:
                            product_name = ""
                            try:
                                _p = await product_service.get_product_by_id(db, str(variant_record.product_id))
                                product_name = _p.name
                            except Exception:
                                pass
                            await websocket_service.broadcast(
                                utils.WebSocketEvent.LOW_STOCK_ALERT.value,
                                {
                                    "variant_id": str(variant_record.id),
                                    "product_id": str(variant_record.product_id),
                                    "product_name": product_name,
                                    "attributes": variant_record.attributes,
                                    "inventory_quantity": variant_record.inventory_quantity,
                                    "low_stock_threshold": threshold,
                                },
                            )
                        except Exception:
                            pass

        await db.commit()
        await cart_service.delete_cart(db, cart.id)

        try:
            await websocket_service.broadcast(utils.WebSocketEvent.NEW_ORDER.value, {
                "order_id": str(order.id),
                "order_number": order_number,
                "customer_name": customer.name,
                "total_amount": float(total_amount),
                "items_count": len(cart_items),
            })
        except Exception:
            pass

        delivery_display = f"{address.address_line}, {address.city}, {address.state}"
        if address.landmark:
            delivery_display += f" (Landmark: {address.landmark})"

        # Include payment details in the order confirmation
        payment_info = ""
        try:
            accounts = await bank_account_service.get_all_bank_accounts(db)
            if accounts:
                default_account = next(
                    (a for a in accounts if a.is_default), accounts[0]
                )
                payment_info = (
                    f"\n\nTo complete payment, transfer *NGN {total_amount:,.2f}* to:\n\n"
                    f"• Bank: *{default_account.bank_name}*\n"
                    f"• Account: *{default_account.account_number}*\n"
                    f"• Name: *{default_account.account_name}*\n\n"
                    f"After payment, send your proof of payment (screenshot or receipt) so we can confirm it."
                )
        except Exception:
            pass

        # Send order confirmation with interactive "Change Address" button
        customer_phone = config["configurable"].get("customer_whatsapp_number")
        confirmation_body = (
            f"Order placed successfully!\n\n"
            f"• Order Number: *{order_number}*\n"
            f"• Status: *{order.status}*\n"
            f"• Total: *NGN {total_amount:,.2f}*\n"
            f"• Delivery Address: {delivery_display}"
            f"{payment_info}"
        )
        if customer_phone:
            try:
                await whatsapp_service.send_interactive_buttons(
                    to=customer_phone,
                    body=confirmation_body,
                    buttons=[
                        {"id": f"chgaddr|{order_number}", "title": "Change Address"},
                    ],
                )
            except Exception:
                await whatsapp_service.send_message(to=customer_phone, body=confirmation_body)

        return (
            f"Order {order_number} placed. Total: NGN {total_amount:,.2f}. "
            f"Delivery: {delivery_display}. Confirmation sent to customer."
        )
    except Exception as e:
        await db.rollback()
        return f"Sorry, there was an error placing your order: {str(e)}"


@tool
async def make_payment(config: RunnableConfig, order_number: str) -> str:
    """Show the business bank account details for the customer to make a bank transfer payment.
    Use this when a customer wants to pay for an order or asks how to pay.
    Shows the default bank account, or lists all accounts if no default is set."""

    db: AsyncSession = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    # Verify the order exists and belongs to the customer
    try:
        order = await order_service.get_order_by_order_number(db, order_number)
    except Exception:
        return f"No order found with number {order_number}."

    if str(order.customer_id) != customer_id:
        return f"No order found with number {order_number} in your account."

    if order.payment_status == utils.PaymentStatus.COMPLETED.value:
        return f"Order {order_number} has already been paid."

    # Get bank accounts
    accounts = await bank_account_service.get_all_bank_accounts(db)
    if not accounts:
        return "Sorry, no bank account details are available at the moment. Please contact support or should I transfer you to human support?"

    # Try to find the default account
    default_account = next((a for a in accounts if a.is_default), None)

    if default_account:
        return (
            f"To complete your order *{order_number}*, please transfer *NGN {order.total_amount:,.2f}* to:\n\n"
            f"• Bank: *{default_account.bank_name}*\n"
            f"• Account Number: *{default_account.account_number}*\n"
            f"• Account Name: *{default_account.account_name}*\n\n"
            f"After payment, send your proof of payment (screenshot or receipt) so we can confirm it."
        )

    # No default — list all accounts
    lines = []
    for acc in accounts:
        lines.append(
            f"• *{acc.bank_name}*\n"
            f"  Account: *{acc.account_number}*\n"
            f"  Name: *{acc.account_name}*"
        )

    return (
        f"To complete your order *{order_number}*, please transfer *NGN {order.total_amount:,.2f}* to any of these accounts:\n\n"
        + "\n\n".join(lines)
        + "\n\nAfter payment, send your proof of payment (screenshot or receipt) so we can confirm it."
    )


@tool
async def update_order_address(
    config: RunnableConfig,
    order_number: str,
    new_address_id: str = None,
    use_default_address: bool = False,
) -> str:
    """ALWAYS call this tool when the customer says 'change address' or 'update address' for an order.
    Call with just order_number (no new_address_id) to send interactive address picker buttons.
    Do NOT list addresses yourself — this tool sends the interactive buttons automatically.
    Args:
        order_number: The order number to update.
        new_address_id: Optional saved address ID. Omit to show address picker.
        use_default_address: Set True to use the customer's default address."""

    db: AsyncSession = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]
    logger.info("update_order_address: called — order={}, addr_id={}", order_number, new_address_id)

    try:
        order = await order_service.get_order_by_order_number(db, order_number)
    except Exception:
        return f"No order found with number {order_number}."

    if str(order.customer_id) != customer_id:
        return f"No order found with number {order_number} in your account."

    if order.status not in [
        utils.OrderStatus.PENDING.value,
        utils.OrderStatus.PAID.value,
    ]:
        return f"Address can only be changed for pending or paid orders. Order {order_number} is currently *{order.status}*."

    # Resolve new address
    address: customer_address_schema.CustomerAddressResponse | None = None

    if use_default_address:
        try:
            address = await customer_address_service.get_default_address(
                db, customer_id
            )
        except Exception:
            return (
                "You don't have a default address saved. Please save an address first."
            )
    elif new_address_id:
        try:
            address = await customer_address_service.get_address_by_id(
                db, new_address_id
            )
            if str(address.customer_id) != str(customer_id):
                return "That address was not found."
        except Exception:
            return "That address was not found."
    else:
        # List saved addresses as interactive buttons
        customer_phone = config["configurable"].get("customer_whatsapp_number")
        addresses = await customer_address_service.get_addresses_by_customer_id(
            db, customer_id
        )
        if addresses and customer_phone:
            rows = []
            for addr in addresses:
                default_tag = " (default)" if addr.is_default else ""
                rows.append({
                    "id": f"addrchg|{order.order_number}|{addr.id}",
                    "title": f"{addr.label.capitalize()}{default_tag}",
                    "description": f"{addr.address_line}, {addr.city}",
                })
            rows.append({
                "id": f"addrchg|{order.order_number}|new",
                "title": "Add new address",
                "description": "Enter a new delivery address",
            })
            sent = False
            try:
                await whatsapp_service.send_interactive_list(
                    to=customer_phone,
                    body=f"Pick a new delivery address for order #{order.order_number}:",
                    button_text="Select address",
                    sections=[{"title": "Saved Addresses", "rows": rows}],
                    header="Change Address",
                )
                sent = True
                logger.info("update_order_address: address list sent successfully")
            except Exception as exc:
                logger.error("update_order_address: FAILED to send address list — {}", exc)

            if sent:
                return (
                    "[INTERACTIVE_SENT] Address picker sent to customer. "
                    "Do NOT send any additional text. Wait silently for their selection."
                )
        elif addresses:
            lines = []
            for i, addr in enumerate(addresses, 1):
                default_tag = " *(default)*" if addr.is_default else ""
                lines.append(
                    f"{i}. *{addr.label.capitalize()}*{default_tag} — {addr.address_line}, {addr.city}"
                )
            return (
                "Which address should I use?\n\n"
                + "\n".join(lines)
                + "\n\nOr you can add a new address first."
            )
        return "You don't have any saved addresses. Please add one first, then I can update the order."

    # Update using service
    await order_service.update_order_address(
        db,
        str(order.id),
        customer_address_schema.CustomerAddressSchema(
            customer_id=customer_id,
            label=address.label,
            full_name=address.full_name,
            phone_number=address.phone_number,
            address_line=address.address_line,
            city=address.city,
            state=address.state,
            country=address.country,
            postal_code=address.postal_code,
            landmark=address.landmark,
        ),
    )

    delivery_display = f"{address.address_line}, {address.city}, {address.state}"
    if address.landmark:
        delivery_display += f" (Landmark: {address.landmark})"

    return (
        f"Delivery address updated for order *{order_number}*!\n\n"
        f"• New address: {delivery_display}"
    )


@tool
async def check_order_status(config: RunnableConfig, order_number: str = None) -> str:
    """Check the status of customer's orders with item details.
    If an order number is provided, shows that specific order.
    Otherwise shows all orders as individual cards with items.
    Pending/paid orders get a Change Address button."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]
    customer_phone = config["configurable"].get("customer_whatsapp_number")

    if order_number:
        try:
            # Use service for lookup (handles fuzzy matching), then fetch ORM for items
            order_resp = await order_service.get_order_by_order_number(db, order_number)
            if str(order_resp.customer_id) != customer_id:
                return f"No order found with number {order_number} in your account."
            result = await db.execute(select(Order).where(Order.id == order_resp.id))
            order = result.scalars().first()
            if not order:
                return f"No order found with number {order_number}."
            await _send_order_card(order, customer_phone)
            return f"Order {order.order_number} details sent."
        except Exception:
            return f"No order found with number {order_number}."

    # Fetch ORM objects directly to get order_items relationship
    result = await db.execute(
        select(Order).where(Order.customer_id == customer_id).order_by(Order.created_at.desc())
    )
    orders = list(result.scalars().all())
    if not orders:
        return "You don't have any orders yet."

    for o in orders:
        await _send_order_card(o, customer_phone)

    return f"Sent {len(orders)} order(s) to the customer."


STATUS_EMOJI = {
    "pending": "🕐", "paid": "💰", "shipped": "🚚",
    "delivered": "✅", "cancelled": "❌",
}

TIMELINE_STEPS = ["pending", "paid", "shipped", "delivered"]


async def _send_order_card(order, customer_phone: str | None):
    """Send a single order as a WhatsApp card with emoji timeline, items, tracking info, and context-dependent buttons."""
    emoji = STATUS_EMOJI.get(order.status, "📦")

    body = (
        f"*Order {order.order_number}*\n"
        f"{emoji} Status: *{order.status.upper()}*  |  Payment: *{order.payment_status}*\n"
        f"Total: *NGN {order.total_amount:,.2f}*"
    )

    # Timeline bar
    if order.status != "cancelled":
        step_index = TIMELINE_STEPS.index(order.status) if order.status in TIMELINE_STEPS else -1
        timeline = " → ".join(
            f"✅ {s.capitalize()}" if i <= step_index else f"⬜ {s.capitalize()}"
            for i, s in enumerate(TIMELINE_STEPS)
        )
        body += f"\n\n{timeline}"
    else:
        body += "\n\n❌ Order Cancelled"

    # Tracking info
    if order.status in ("shipped", "delivered"):
        body += f"\n\n🔍 Tracking ID: *{order.order_number}*"
    if getattr(order, "estimated_delivery_date", None):
        body += f"\n📅 Est. Delivery: *{order.estimated_delivery_date.strftime('%a %d %b %Y')}*"

    # Address
    if order.address_line:
        delivery = f"{order.address_line}, {order.address_city}, {order.address_state}"
        if order.address_landmark:
            delivery += f" (Landmark: {order.address_landmark})"
        body += f"\n📍 Delivery: {delivery}"

    # Items with per-item delivery status
    if order.order_items:
        body += "\n\n*Items:*"
        for item in order.order_items:
            name = item.product_name or "Unknown"
            if item.product_variant_attributes:
                attrs = ", ".join(str(v) for v in item.product_variant_attributes.values())
                name += f" ({attrs})"
            item_line = f"\n• {item.quantity} unit(s) of {name} — NGN {item.subtotal:,.2f}"
            # Show per-item status during partial shipments
            if order.status == "shipped" and item.delivery_status:
                item_emoji = STATUS_EMOJI.get(item.delivery_status, "")
                item_line += f" [{item_emoji} {item.delivery_status}]"
            body += item_line

    if not customer_phone:
        return

    # Context-dependent buttons (max 3)
    buttons = []
    if order.status in (utils.OrderStatus.PENDING.value, utils.OrderStatus.PAID.value):
        buttons.append({"id": f"chgaddr|{order.order_number}", "title": "Change Address"})
        buttons.append({"id": f"cancel|{order.order_number}", "title": "Cancel Order"})
    elif order.status == utils.OrderStatus.SHIPPED.value:
        buttons.append({"id": f"track|{order.order_number}", "title": "Track Again"})

    if buttons:
        try:
            await whatsapp_service.send_interactive_buttons(
                to=customer_phone, body=body, buttons=buttons,
            )
            return
        except Exception as exc:
            logger.error("_send_order_card: button send failed — {}", exc)

    # Fallback: plain text
    try:
        await whatsapp_service.send_message(to=customer_phone, body=body)
    except Exception as exc:
        logger.error("_send_order_card: message send failed — {}", exc)


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


@tool
async def update_my_name(config: RunnableConfig, full_name: str) -> str:
    """Update the customer's full name. Call this when a first-time customer provides their name before placing an order.
    Args:
        full_name: The customer's full name as they provided it."""

    db: AsyncSession = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    result = await db.execute(select(CustomerModel).where(CustomerModel.id == customer_id))
    cust = result.scalars().first()
    if not cust:
        return "Customer not found."

    cust.name = full_name
    # Create a NEW dict — reassigning the same object reference won't be detected by SQLAlchemy
    cust.extra_metadata = {**(cust.extra_metadata or {}), "name_confirmed": True}

    await db.commit()
    # Expire all cached objects so the next query (e.g. place_order in the same session) gets fresh data
    db.expire_all()
    logger.info("update_my_name: customer={} name updated to {!r}", customer_id, full_name)
    return f"Name updated to *{full_name}*. You can now proceed with your order."


order_tools = [
    place_order,
    make_payment,
    update_order_address,
    check_order_status,
    cancel_order,
    update_my_name,
]
