from fastapi import APIRouter
from .endpoints.customer_endpoints import customer_router
from .endpoints.product_endpoints import product_router
from .endpoints.inventory_endpoints import inventory_router
from .endpoints.conversation_endpoints import conversation_router
from .endpoints.message_endpoints import message_router
from .endpoints.cart_endpoints import cart_router
from .endpoints.order_endpoints import order_router
from .endpoints.payment_endpoints import payment_router
from .endpoints.processed_webhook_endpoints import webhook_router
from .endpoints.bank_account_endpoints import bank_account_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(customer_router)
api_router.include_router(product_router)
api_router.include_router(inventory_router)
api_router.include_router(conversation_router)
api_router.include_router(message_router)
api_router.include_router(cart_router)
api_router.include_router(order_router)
api_router.include_router(payment_router)
api_router.include_router(webhook_router)
api_router.include_router(bank_account_router)
