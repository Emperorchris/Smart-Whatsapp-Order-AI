from ..graph.agent_state import AgentState
from ...services import product_service
from sqlalchemy.orm import Session
from langchain_core.messages import AIMessage, HumanMessage
from ...core.config import Config
from langchain_openai import ChatOpenAI
from ...db.schemas import product_schema
from ...services.product_variant_service import get_variants_by_product_id


llm = ChatOpenAI(model=Config.OPENAI_LLM_MODEL, temperature=0)

structured_llm = llm.with_structured_output(product_schema.ProductSearchParams)


def product_lookup_node(state: AgentState, db: Session) -> AgentState:

    # For simplicity, we assume the product name is mentioned in the latest message
    latest_message = state["messages"][-1].content if state["messages"] else ""

    structured_llm_output = structured_llm.invoke(
        [HumanMessage(content=latest_message)])

    products = product_service.search_products(
        db,
        name=structured_llm_output.name,
        description=structured_llm_output.description,
        category_id=structured_llm_output.category_id,
        sku=structured_llm_output.sku,
        min_price=structured_llm_output.min_price,
        max_price=structured_llm_output.max_price,
        is_active=structured_llm_output.is_active
    )
    
    if not products:
        reply = "Sorry, I couldn't find any products matching your request."
    else:
        lines = []
        for p in products[:10]:  # Limit to top 10 results
            line = f"*{p.name}* - *NGN{p.price}*"
            
            variants = get_variants_by_product_id(db, p.id)
            if variants:
                variant_lines = [f"  - {', '.join(f'{k}: {val}' for k, val in v.attributes.items())} - *NGN{v.product_variant_price}*" for v in variants]
                line += "\n" + "\n".join(variant_lines)
                
                in_stock = sum(1 for v in variants if v.inventory_quantity > 0)
                line += f" ({in_stock} variants in stock)"

            lines.append(line)
        
        reply = "Here are the products I found:\n\n" + "\n\n".join(lines)
   
    return {
        "messages": [AIMessage(content=reply)],
        "search_results": products
    }


