from ..graph.agent_state import AgentState
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage
from ...core.config import Config
from langchain_openai import ChatOpenAI
from ...services import order_service, product_service, cart_service, customer_service
from ...db.schemas import order_schema, cart_schema, cart_item_schema, order_item_schema
from ...services import order_item_service
from pydantic import BaseModel
from ...core import utils
from ...core import common


llm = ChatOpenAI(model=Config.OPENAI_LLM_MODEL, temperature=0)

class OrderAction(BaseModel):
    action: utils.OrderActionType
    order_number: str | None = None
    extra_metadata: dict | None = None
    customer_address: str | None = None


structured_llm = llm.with_structured_output(OrderAction)

def order_node(state: AgentState, config: RunnableConfig) -> AgentState:
    db = config["configurable"]["db"]
    """
        Handles order-related intents:
        - place_order: Create order from cart
        - check_status: Show customer's order history and statuses
        - cancel_order: Cancel an existing order (if pending)
    """
    
    latest_message = state["messages"][-1].content if state["messages"] else ""
    customer_id = state["customer_id"]
    params: OrderAction = structured_llm.invoke([HumanMessage(content=latest_message)])
    

    action = params.action
    order_number = params.order_number
    
    if action == utils.OrderActionType.PLACE_ORDER:
        # Get active cart for customer
        cart: cart_schema.CartResponse = cart_service.get_cart_by_customer_id(db, customer_id)
        if not cart:
            reply = "You don't have any items in your cart. Please add products to your cart before placing an order."
        else:
            # Create order from cart
            customer = customer_service.get_customer_by_id(db, customer_id)
            cart_items: list[cart_item_schema.CartItemResponse] = cart.cart_items
            
            if not cart_items:
                reply = "Your cart is empty. Please add products to your cart before placing an order."
            else:
                try:
                    order_number = common.generate_order_number()
                    # total_amount = sum(item.unit_price * item.quantity for item in cart_items)
                    total_amount = sum(item.subtotal for item in cart_items)
                    
                    order_data = order_schema.OrderSchema(
                        customer_id=customer_id,
                        customer_name=customer.display_name,
                        customer_whatsapp_number=customer.whatsapp_number,
                        order_number=order_number,
                        total_amount=total_amount,
                        delivery_address=params.customer_address or "No address provided",
                        extra_metadata=params.extra_metadata
                    )
                    
                    order = order_service.create_order(db, order_data)
                    
                    for item in cart_items:
                        product = product_service.get_product_by_id(db, item.product_id)
                        if not product:
                            continue  # Skip if product no longer exists
                        
                        order_item_data = order_item_schema.OrderItemSchema(
                            order_id=order.id,
                            product_id=item.product_id,
                            product_name=product.name,
                            product_sku=product.sku,
                            quantity=item.quantity,
                            unit_price=item.unit_price,
                            subtotal=item.subtotal
                        )
                        order_item_service.create_order_item(db, order_item_data)
                    
                    cart_service.delete_cart(db, cart.id)
            
                    reply = (
                        f"✅ Order placed successfully!\n"
                        f"Order Number: *{order_number}*\n"
                        f"Total: *NGN{total_amount}*\n\n"
                        f"You can check your order status anytime by asking 'What is the status of my order?'"
                    )
                except Exception as e:
                    reply = f"Sorry, there was an error placing your order. Error: {str(e)}"
                    
    elif action == utils.OrderActionType.CHECK_STATUS:
        orders = order_service.get_orders_by_customer_id(db, customer_id)
        if not orders:
            reply = "You don't have any orders yet. Place an order to see it here."
        else:
            lines = []
            for o in orders:
                line = f"Order *{o.order_number}* - Status: *{o.status}* - Total: *NGN{o.total_amount}*"
                lines.append(line)
            reply = "Here are your orders:\n\n" + "\n\n".join(lines)
            
    elif action == utils.OrderActionType.CANCEL_ORDER:
        if not order_number:
            reply = "Please specify the order number you want to cancel."
        else:
            order = order_service.get_order_by_order_number(db, order_number)
            if not order or order.customer_id != customer_id:
                reply = f"Sorry, I couldn't find an order with number {order_number} in your account."
            elif order.status != utils.OrderStatus.PENDING.value:
                reply = f"Sorry, only orders that are still pending can be cancelled. Your order {order_number} is currently {order.status}."
            else:
                order_service.cancel_order(db, order.id)
                reply = f"Your order {order_number} has been cancelled successfully."
    else:
        reply = "Sorry, I didn't understand your request. You can ask me to place an order, check your order status, or cancel an order."
        
    return {
        "messages": [AIMessage(content=reply)],
        "order_action": action,
    }
    
