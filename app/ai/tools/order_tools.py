from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...services import (
    order_service,
    product_service,
    cart_service,
    customer_service,
    order_item_service,
    customer_address_service,
    whatsapp_service,
    bank_account_service,
)
from ...services.product_variant_service import get_variant_by_id
from ...db.schemas import order_schema, order_item_schema, customer_address_schema
from ...db.model import product_variant_model
from ...core import utils, common


@tool
async def place_order(
    config: RunnableConfig,
    customer_address_id: str = None,
    # customer_address: customer_address_schema.CustomerAddressSchema = None,
    # address_line: str = "",
    # city: str = "",
    # state: str = "",
    # landmark: str = "",
    use_default_address: bool = False,
) -> str:
    """Place an order from the customer's current cart.
    Use this when a customer wants to checkout or place an order.
    Either set use_default_address=True to use the customer's saved default address,
    or provide address_line, city, and state for a new delivery address.
    If no address is provided at all, ask the customer for their delivery address before placing the order."""

    db: AsyncSession = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    try:
        customer = await customer_service.get_customer_by_id(db, customer_id)
    except Exception:
        return "Customer not found"

    try:
        cart = await cart_service.get_cart_by_customer_id(db, customer_id)
    except Exception:
        return "You don't have any items in your cart. Please add products before placing an order."

    cart_items = cart.cart_items
    if not cart_items:
        return "Your cart is empty. Please add products before placing an order."

    # Resolve delivery address
    address: customer_address_schema.CustomerAddressResponse | None = None

    if use_default_address:
        try:
            address = await customer_address_service.get_default_address(
                db, customer_id
            )
        except Exception:
            return "You don't have a default address saved. Please provide a delivery address or save one first."
    elif customer_address_id:
        try:
            address = await customer_address_service.get_address_by_id(
                db, customer_address_id
            )
        except Exception:
            return "That address was not found. Please provide a valid address or use your default."
    else:
        # No address provided — prompt the customer to add or select one
        addresses = await customer_address_service.get_addresses_by_customer_id(
            db, customer_id
        )
        if addresses:
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
        # Send interactive list to collect address
        customer_phone = config["configurable"].get("customer_whatsapp_number", "")
        logger.info("place_order: customer_phone from config = {!r}", customer_phone)
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
            try:
                result = await whatsapp_service.send_interactive_list(
                    to=customer_phone,
                    body="You need a delivery address to place your order. What type of address is this?",
                    button_text="Select type",
                    sections=sections,
                    header="Delivery Address",
                    footer="Step 1 of 2",
                )
                logger.info("place_order: interactive list sent successfully — {}", result)
            except Exception as exc:
                logger.error("place_order: FAILED to send interactive list — {}", exc)
            return (
                "I've sent the customer an interactive list to pick their address type. "
                "Wait for their selection, then ask for the full address details: street address, city, state, and a landmark."
            )

        return "Please provide a delivery address before I can place your order. Send me your street address, city, state, and a landmark if any."

    # Check stock
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

        await db.commit()
        await cart_service.delete_cart(db, cart.id)

        delivery_display = f"{address.address_line}, {address.city}, {address.state}"
        if address.landmark:
            delivery_display += f" (Landmark: {address.landmark})"

        # Include payment details in the order confirmation
        payment_info = ""
        try:
            accounts = await bank_account_service.get_all_bank_accounts(db)
            if accounts:
                default_account = next((a for a in accounts if a.is_default), accounts[0])
                payment_info = (
                    f"\n\nTo complete payment, transfer *NGN {total_amount:,.2f}* to:\n\n"
                    f"• Bank: *{default_account.bank_name}*\n"
                    f"• Account: *{default_account.account_number}*\n"
                    f"• Name: *{default_account.account_name}*\n\n"
                    f"After payment, send your proof of payment (screenshot or receipt) so we can confirm it."
                )
        except Exception:
            pass

        return (
            f"Order placed successfully!\n\n"
            f"• Order Number: *{order_number}*\n"
            f"• Status: *{order.status}*\n"
            f"• Total: *NGN {total_amount:,.2f}*\n"
            f"• Delivery Address: {delivery_display}\n\n"
            f"Review your delivery address. If it's incorrect, reply with *Change Address* to update it before the order is processed."
            f"{payment_info}"
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
    """Update the delivery address for an existing order that hasn't been processed yet.
    Use this when a customer wants to change the delivery address for an order they just placed.
    Either provide new_address_id (ID of a saved address) or set use_default_address=True."""

    db: AsyncSession = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

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
        except Exception:
            return "That address was not found."
    else:
        # List saved addresses for the customer to pick
        addresses = await customer_address_service.get_addresses_by_customer_id(
            db, customer_id
        )
        if addresses:
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


order_tools = [
    place_order,
    make_payment,
    update_order_address,
    check_order_status,
    cancel_order,
]
