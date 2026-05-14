from ..graph.agent_state import AgentState
from sqlalchemy.orm import Session
from langchain_core.messages import AIMessage, HumanMessage
from ...core.config import Config
from langchain_openai import ChatOpenAI
from ...services import cart_service, product_service, cart_item_service, customer_service
from ...db.schemas import cart_schema, cart_item_schema, customers_schema
from ...core.utils import CartActionType
from ...db.model import customer_model, carts_model