from ..graph.agent_state import AgentState
from ...services import product_service
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from ...core.config import Config
from langchain_openai import ChatOpenAI
from ...db.schemas import product_schema
from ...services.product_variant_service import get_variants_by_product_id


llm = ChatOpenAI(model=Config.OPENAI_LLM_MODEL, temperature=0)

structured_llm = llm.with_structured_output(product_schema.ProductSearchParams)

EXTRACT_PROMPT = SystemMessage(content="""
Extract product search parameters from the customer's message.
It might be product list.
Pull out any product name, description keywords, price range, or SKU mentioned.
If something is not mentioned, leave it as null.
""")


def product_lookup_node(state: AgentState, config: RunnableConfig) -> AgentState:
    db = config["configurable"]["db"]

    latest_message = state["messages"][-1].content if state["messages"] else ""

    try:
        structured_llm_output: product_schema.ProductSearchParams = structured_llm.invoke(
            [EXTRACT_PROMPT, HumanMessage(content=latest_message)]
        )
    except Exception:
        # If structured output fails, fall back to searching by the raw message text
        structured_llm_output = product_schema.ProductSearchParams(name=latest_message)

    products = product_service.search_products(
        db,
        name=structured_llm_output.name,
        description=structured_llm_output.description,
        category_id=structured_llm_output.category_id,
        sku=structured_llm_output.sku,
        min_price=structured_llm_output.min_price,
        max_price=structured_llm_output.max_price,
        is_active=structured_llm_output.is_active,
    )

    if not products:
        reply = "Sorry, I couldn't find any products matching your request."
    else:
        lines = []
        for p in products[:10]:  # Limit to top 10 results
            line = f"*{p.name}* - *NGN{p.price}*"

            variants = get_variants_by_product_id(db, p.id)
            if variants:
                variant_lines = [
                    f"  - {', '.join(f'{k}: {val}' for k, val in v.attributes.items())} - *NGN{v.product_variant_price}*"
                    for v in variants
                ]
                line += "\n" + "\n".join(variant_lines)

                in_stock = sum(1 for v in variants if v.inventory_quantity > 0)
                line += f" ({in_stock} variants in stock)"

            lines.append(line)

        reply = "Here are the products I found:\n\n" + "\n\n".join(lines)

    # Collect all images from found products
    media_urls = []
    if products:
        for p in products[:10]:
            if p.media:
                media_urls.extend([item.url for item in p.media])
                
    return {"messages": [AIMessage(content=reply)], "search_results": products, "media_urls": media_urls}