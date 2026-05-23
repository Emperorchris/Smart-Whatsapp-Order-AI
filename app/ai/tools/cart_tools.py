from typing import Optional
from loguru import logger
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...services import cart_service, product_service, cart_item_service
from ...services.product_variant_service import get_variants_by_product_id, get_variant_by_id
from ...db.schemas import cart_schema, cart_item_schema


@tool
async def add_to_cart(
    config: RunnableConfig,
    product_name: str,
    quantity: int = 1,
    variant_attributes: Optional[str] = None,
) -> str:
    """Add a product to the customer's cart.
    Use this when a customer wants to add an item to their cart.
    Searches for the product by name and adds the specified quantity.
    If the product has variants, specify variant_attributes like 'size: M, color: Red' to select the right one.
    If the product has variants but no variant_attributes is provided, list the available variants for the customer to choose."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    logger.info(
        "add_to_cart called — product_name={!r}, quantity={}, variant_attributes={!r}, customer_id={}",
        product_name, quantity, variant_attributes, customer_id,
    )

    products = await product_service.search_products(db, name=product_name)
    if not products:
        logger.warning("add_to_cart: no products found for name={!r}", product_name)
        return f"Sorry, I couldn't find a product called '{product_name}'."

    product = products[0]
    logger.info("add_to_cart: matched product id={} name={!r}", product.id, product.name)

    variants = await get_variants_by_product_id(db, str(product.id))
    variant = None
    unit_price = product.price

    if variants:
        logger.info("add_to_cart: product has {} variants", len(variants))

        if not variant_attributes:
            variant_lines = []
            for v in variants:
                attrs = ", ".join(f"{k}: {val}" for k, val in v.attributes.items())
                stock = f"({v.inventory_quantity} in stock)" if v.inventory_quantity > 0 else "(Out of stock)"
                variant_lines.append(f"• {attrs} - NGN {v.product_variant_price:,.2f} {stock}")
            logger.info("add_to_cart: no variant_attributes provided, returning variant list to LLM")
            return (
                f"*{product.name}* has multiple variants. Which one would you like?\n\n"
                + "\n".join(variant_lines)
                + "\n\nPlease specify the variant you want (e.g. size and color)."
            )

        parsed_attrs = {}
        for pair in variant_attributes.split(","):
            pair = pair.strip()
            if ":" in pair:
                k, v_val = pair.split(":", 1)
                parsed_attrs[k.strip().lower()] = v_val.strip().lower()

        logger.info("add_to_cart: parsed_attrs={!r} (raw variant_attributes={!r})", parsed_attrs, variant_attributes)

        variant = None
        for v in variants:
            v_attrs = {k.lower(): str(val).lower() for k, val in v.attributes.items()}
            match = all(v_attrs.get(k) == val for k, val in parsed_attrs.items())
            logger.debug("add_to_cart: comparing parsed_attrs={!r} against db_attrs={!r} → match={}", parsed_attrs, v_attrs, match)
            if match:
                variant = v
                break

        if not variant:
            db_variants_dump = [
                {k.lower(): str(val).lower() for k, val in v.attributes.items()}
                for v in variants
            ]
            logger.warning(
                "add_to_cart: VARIANT MATCH FAILED — parsed_attrs={!r} did not match any of {!r}",
                parsed_attrs, db_variants_dump,
            )
            variant_lines = []
            for v in variants:
                attrs = ", ".join(f"{k}: {val}" for k, val in v.attributes.items())
                variant_lines.append(f"• {attrs} - NGN {v.product_variant_price:,.2f}")
            return (
                f"I couldn't find that variant. Available options for *{product.name}*:\n\n"
                + "\n".join(variant_lines)
            )

        logger.info("add_to_cart: matched variant id={} attrs={!r}", variant.id, variant.attributes)

        if variant.inventory_quantity < quantity:
            if variant.inventory_quantity == 0:
                return f"Sorry, that variant of *{product.name}* is currently out of stock."
            return (
                f"Sorry, only {variant.inventory_quantity} unit(s) of that variant are available. "
                f"Would you like to add {variant.inventory_quantity} instead?"
            )

        unit_price = variant.product_variant_price

    try:
        cart = await cart_service.get_cart_by_customer_id(db, customer_id)
        logger.info("add_to_cart: found existing cart id={}", cart.id)
    except Exception as exc:
        logger.info("add_to_cart: no active cart found ({}), creating new one", exc)
        try:
            await db.rollback()
            cart = await cart_service.create_cart(db, cart_schema.CartSchema(customer_id=customer_id))
            logger.info("add_to_cart: created cart id={}", cart.id)
        except Exception as create_exc:
            logger.error("add_to_cart: FAILED to create cart — {}", create_exc, exc_info=True)
            return "Sorry, something went wrong setting up your cart. Please try again."

    existing_items = await cart_item_service.get_cart_items_by_cart_id(db, str(cart.id))
    variant_id = str(variant.id) if variant else None
    existing_item = next(
        (
            item
            for item in existing_items
            if str(item.product_id) == str(product.id)
            and str(item.variant_id or "") == str(variant_id or "")
        ),
        None,
    )

    try:
        if existing_item:
            new_qty = existing_item.quantity + quantity
            logger.info("add_to_cart: updating existing cart item id={}, new_qty={}", existing_item.id, new_qty)
            await cart_item_service.update_cart_item(
                db,
                cart_item_id=str(existing_item.id),
                cart_item_data=cart_item_schema.CartItemSchema(
                    cart_id=str(cart.id),
                    product_id=str(product.id),
                    variant_id=variant_id,
                    quantity=new_qty,
                    unit_price=unit_price,
                    subtotal=unit_price * new_qty,
                ),
            )
        else:
            logger.info("add_to_cart: creating new cart item — cart_id={} product_id={} variant_id={}", cart.id, product.id, variant_id)
            await cart_item_service.create_cart_item(
                db,
                cart_item_schema.CartItemSchema(
                    cart_id=str(cart.id),
                    product_id=str(product.id),
                    variant_id=variant_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=unit_price * quantity,
                ),
            )
    except Exception as exc:
        logger.error("add_to_cart: FAILED to save cart item — {}", exc)
        return f"Sorry, something went wrong adding *{product.name}* to your cart. Please try again."

    variant_desc = ""
    if variant:
        attrs = ", ".join(f"{k}: {val}" for k, val in variant.attributes.items())
        variant_desc = f" ({attrs})"

    logger.info("add_to_cart: SUCCESS — added {}{} to cart", product.name, variant_desc)
    return f"Added {quantity} unit(s) of *{product.name}*{variant_desc} @ NGN {unit_price:,.2f} each to your cart."


@tool
async def remove_from_cart(config: RunnableConfig, product_name: str) -> str:
    """Remove a product from the customer's cart by name.
    Use this when a customer wants to remove an item from their cart."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    try:
        cart = await cart_service.get_cart_by_customer_id(db, customer_id)
    except Exception:
        return "Your cart is empty. There's nothing to remove."

    items = await cart_item_service.get_cart_items_by_cart_id(db, str(cart.id))

    for item in items:
        try:
            product = await product_service.get_product_by_id(db, str(item.product_id))
            if product_name.lower() in product.name.lower():
                await cart_item_service.delete_cart_item(db, str(item.id))
                return f"Removed *{product.name}* from your cart."
        except Exception:
            continue

    return f"I couldn't find '{product_name}' in your cart."


@tool
async def view_cart(config: RunnableConfig) -> str:
    """View the contents of the customer's cart.
    Use this when a customer wants to see what's in their cart."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    try:
        cart = await cart_service.get_cart_by_customer_id(db, customer_id)
    except Exception:
        return "Your cart is empty."

    items = await cart_item_service.get_cart_items_by_cart_id(db, str(cart.id))
    if not items:
        return "Your cart is empty."

    total = 0
    descriptions = []
    for item in items:
        try:
            product = await product_service.get_product_by_id(db, str(item.product_id))
            name = product.name
        except Exception:
            name = "Unknown product"

        if item.variant_id:
            try:
                variant = await get_variant_by_id(db, str(item.variant_id))
                attrs = ", ".join(f"{k}: {val}" for k, val in variant.attributes.items())
                name += f" ({attrs})"
            except Exception:
                pass

        subtotal = item.unit_price * item.quantity
        total += subtotal
        descriptions.append(f"• {item.quantity} unit(s) of {name} @ NGN {item.unit_price:,.2f}")

    item_count = len(descriptions)
    result = f"You have {item_count} item(s) in your cart totaling *NGN {total:,.2f}*\n\n"
    result += "\n".join(descriptions)
    return result


@tool
async def clear_cart(config: RunnableConfig) -> str:
    """Clear all items from the customer's cart.
    Use this when a customer wants to empty their entire cart."""

    db = config["configurable"]["db"]
    customer_id = config["configurable"]["customer_id"]

    try:
        cart = await cart_service.get_cart_by_customer_id(db, customer_id)
    except Exception:
        return "Your cart is already empty."

    items = await cart_item_service.get_cart_items_by_cart_id(db, str(cart.id))
    for item in items:
        await cart_item_service.delete_cart_item(db, str(item.id))

    return "Your cart has been cleared."



cart_tools = [add_to_cart, remove_from_cart, view_cart, clear_cart]
