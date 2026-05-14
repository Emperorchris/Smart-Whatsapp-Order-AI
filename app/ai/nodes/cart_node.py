from ..graph.agent_state import AgentState
from sqlalchemy.orm import Session
from langchain_core.messages import AIMessage, HumanMessage
from ...core.config import Config
from langchain_openai import ChatOpenAI
from ...services import cart_service, product_service, cart_item_service
from ...db.schemas import cart_schema, cart_item_schema
from ...core.utils import CartActionType
from ...db.model import carts_model

llm = ChatOpenAI(model=Config.OPENAI_LLM_MODEL, temperature=0)

structure_llm = llm.with_structured_output(cart_schema.CartAction)


def cart_node(state: AgentState, db: Session) -> AgentState:
    latest_message = state["messages"][-1].content if state["messages"] else ""
    customer_id = state["customer_id"]

    params: cart_schema.CartAction = structure_llm.invoke(
        [HumanMessage(content=latest_message)])

    carts = cart_service.get_carts_by_customer_id(db, customer_id)
    cart: carts_model.Cart | None = carts[0] if carts else None

    action = params.action

    if action == CartActionType.ADD:
        if not params.product_name:
            reply = "Please tell me the product name you want to add."
            return {
                "messages": [AIMessage(content=reply)],
                "cart_id": str(cart.id) if cart else None
            }

        search_products = product_service.search_products(
            db,
            name=params.product_name,
        )

        if not search_products:
            reply = f"Sorry, I couldn't find a product called '{params.product_name}'."
        else:
            product = search_products[0]  # Take the first matching product

            if not cart:
                cart = cart_service.create_cart(
                    db, cart_schema.CartSchema(customer_id=customer_id))

            existing_items = cart_item_service.get_cart_items_by_cart_id(
                db, str(cart.id))
            existing_item = None
            for item in existing_items:
                if str(item.product_id) == str(product.id):
                    existing_item = item
                    break

            if existing_item:
                new_qty = existing_item.quantity + params.quantity
                cart_item_service.update_cart_item(
                    db,
                    cart_item_id=str(existing_item.id),
                    cart_item_data=cart_item_schema.CartItemSchema(
                        cart_id=str(cart.id),
                        product_id=str(product.id),
                        quantity=new_qty,
                        unit_price=product.price,
                        subtotal=product.price * new_qty
                    )
                )
            else:
                cart_item_service.create_cart_item(
                    db,
                    cart_item_schema.CartItemSchema(
                        cart_id=str(cart.id),
                        product_id=str(product.id),
                        quantity=params.quantity,
                        unit_price=product.price,
                        subtotal=product.price * params.quantity
                    )
                )

            reply = f"Added {params.quantity} of '{product.name}' to your cart."

    elif action == CartActionType.REMOVE:
        if not params.product_name:
            reply = "Please tell me the product name you want to remove."
            return {
                "messages": [AIMessage(content=reply)],
                "cart_id": str(cart.id) if cart else None
            }

        if not cart:
            reply = "Your cart is empty. There's nothing to remove."
        else:
            existing_items = cart_item_service.get_cart_items_by_cart_id(
                db, str(cart.id))
            item_to_remove = None
            for item in existing_items:
                product = product_service.get_product_by_id(db, str(item.product_id))
                if params.product_name.lower() in product.name.lower():
                    item_to_remove = item
                    break

            if item_to_remove:
                cart_item_service.delete_cart_item(db, str(item_to_remove.id))
                reply = f"Removed *{product.name}* from your cart."
            else:
                reply = f"I couldn't find '{params.product_name}' in your cart."

    elif action == CartActionType.UPDATE:
        if not params.product_id:
            reply = "Please provide the product you want to update in your cart."
            return {
                "messages": [AIMessage(content=reply)],
                "cart_id": str(cart.id) if cart else None
            }

        if params.quantity < 1:
            reply = "Quantity must be at least 1."
            return {
                "messages": [AIMessage(content=reply)],
                "cart_id": str(cart.id) if cart else None
            }

        if not cart:
            reply = "Your cart is empty. There's nothing to update."
        else:
            existing_items = cart_item_service.get_cart_items_by_cart_id(
                db, str(cart.id))
            item_to_update = None
            for item in existing_items:
                if str(item.product_id) == str(params.product_id):
                    item_to_update = item
                    break

            if item_to_update:
                cart_item_service.update_cart_item(
                    db,
                    cart_item_id=str(item_to_update.id),
                    cart_item_data=cart_item_schema.CartItemSchema(
                        cart_id=str(cart.id),
                        product_id=str(params.product_id),
                        quantity=params.quantity,
                        unit_price=item_to_update.unit_price,
                        subtotal=item_to_update.unit_price * params.quantity
                    )
                )
                reply = "Cart updated."
            else:
                reply = "I couldn't find that product in your cart."

    elif action == CartActionType.VIEW:
        if not cart:
            reply = "Your cart is empty."
        else:
            items = cart_item_service.get_cart_items_by_cart_id(
                db, str(cart.id))
            if not items:
                reply = "Your cart is empty."
            else:
                item_descriptions = []
                for item in items:
                    try:
                        product = product_service.get_product_by_id(
                            db, str(item.product_id))
                        product_name = product.name
                    except Exception:
                        product_name = "Unknown product"

                    item_descriptions.append(
                        f"{item.quantity} x {product_name} (NGN{item.unit_price} each)")
                reply = "Your cart contains:\n" + "\n".join(item_descriptions)
    elif action == CartActionType.CLEAR:
        if not cart:
            reply = "Your cart is already empty."
        else:
            items = cart_item_service.get_cart_items_by_cart_id(
                db, str(cart.id))
            for item in items:
                cart_item_service.delete_cart_item(db, str(item.id))
            reply = "Your cart has been cleared."
    else:
        reply = "Sorry, I didn't understand that action. Please specify add, remove, update, view, or clear."

    return {
        "messages": [AIMessage(content=reply)],
        "cart_id": str(cart.id) if cart else None
    }
