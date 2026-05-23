from typing import Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from ...services import product_service
from ...services.product_variant_service import get_variants_by_product_id


@tool
async def search_products(
    config: RunnableConfig,
    name: Optional[str] = None,
    description: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sku: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
) -> str:
    """Search for products in the store by name, description, price range, or SKU.
    Use this when a customer asks about products, prices, availability, or wants to browse.
    Use skip and limit for pagination. For example, skip=0 limit=10 for the first 10, skip=10 limit=10 for the next 10.
    Returns a formatted list of matching products with prices and variants."""

    db = config["configurable"]["db"]

    products = await product_service.search_products(
        db,
        name=name,
        description=description,
        min_price=min_price,
        max_price=max_price,
        sku=sku,
        skip=skip,
        limit=limit,
    )

    if not products:
        return "No products found matching your search."

    blocks = []

    for p in products:
        line = f"*{p.name}*\nPrice: *NGN {p.price:,.2f}*"

        variants = await get_variants_by_product_id(db, p.id)
        if variants:
            variant_lines = [
                f"• {', '.join(f'{k}: {val}' for k, val in v.attributes.items())} - NGN {v.product_variant_price:,.2f}"
                for v in variants
            ]
            line += "\n" + "\n".join(variant_lines)

            in_stock = sum(1 for v in variants if v.inventory_quantity > 0)
            line += f"\n({in_stock} variants in stock)"

        if p.media:
            media = next((item for item in p.media if item.type == "image"), None)

            if not media:
                media = next(
                    (item for item in p.media if item.type == "live_image"), None
                )

            if not media:
                media = next((item for item in p.media if item.type == "video"), None)

            if media:
                line += f"\n[PRODUCT_MEDIA]{media.url}[/PRODUCT_MEDIA]"

        blocks.append(f"[PRODUCT_START]\n{line}\n[PRODUCT_END]")

    result = "Here are the products we have:\n\n" + "\n\n".join(blocks)
    return result


@tool
async def get_product_details(config: RunnableConfig, product_name: str) -> str:
    """Get detailed information about a specific product by name.
    Use this when a customer asks about a specific product's details, variants, or availability."""

    db = config["configurable"]["db"]

    products = await product_service.search_products(db, name=product_name)

    if not products:
        return f"No product found matching '{product_name}'."

    p = products[0]
    details = f"*{p.name}*\n"
    details += f"Price: *NGN {p.price:,.2f}*\n"
    if p.description:
        details += f"{p.description}\n"
    if p.sku:
        details += f"SKU: {p.sku}\n"

    variants = await get_variants_by_product_id(db, p.id)
    if variants:
        details += "\nAvailable variants:\n"
        for v in variants:
            attrs = ", ".join(f"{k}: {val}" for k, val in v.attributes.items())
            stock = "In stock" if v.inventory_quantity > 0 else "Out of stock"
            details += f"• {attrs} - NGN {v.product_variant_price:,.2f} ({stock})\n"

    if p.media:
        media = next((item for item in p.media if item.type == "image"), None)

        if not media:
            media = next(
                (item for item in p.media if item.type == "live_image"), None
            )

        if not media:
            media = next((item for item in p.media if item.type == "video"), None)

        if media:
            details += f"\n[PRODUCT_MEDIA]{media.url}[/PRODUCT_MEDIA]"

    return f"[PRODUCT_START]\n{details}\n[PRODUCT_END]"


async def _find_product(db, product_name: str):
    products = await product_service.search_products(db, name=product_name)
    if not products:
        return None, f"No product found matching '{product_name}'."
    return products[0], None


@tool
async def get_product_media(config: RunnableConfig, product_name: str) -> str:
    """Get all media (images and videos) for a specific product.
    Use this when a customer asks to see all photos and videos of a product."""

    db = config["configurable"]["db"]
    p, err = await _find_product(db, product_name)
    if err:
        return err

    if not p.media:
        return f"*{p.name}* doesn't have any media available."

    urls = ",".join(item.url for item in p.media)
    caption = f"All media for *{p.name}* ({len(p.media)} items)"

    return f"[PRODUCT_START]\n{caption}\n[PRODUCT_MEDIA]{urls}[/PRODUCT_MEDIA]\n[PRODUCT_END]"


@tool
async def get_product_images(config: RunnableConfig, product_name: str) -> str:
    """Get only images (no videos) for a specific product.
    Use this when a customer asks to see photos or pictures of a product."""

    db = config["configurable"]["db"]
    p, err = await _find_product(db, product_name)
    if err:
        return err

    if not p.media:
        return f"*{p.name}* doesn't have any images available."

    images = [item for item in p.media if item.type in ("image", "live_image")]
    if not images:
        return f"*{p.name}* doesn't have any images available."

    urls = ",".join(item.url for item in images)
    caption = f"Images for *{p.name}* ({len(images)} photos)"

    return f"[PRODUCT_START]\n{caption}\n[PRODUCT_MEDIA]{urls}[/PRODUCT_MEDIA]\n[PRODUCT_END]"


@tool
async def get_product_videos(config: RunnableConfig, product_name: str) -> str:
    """Get only videos (no images) for a specific product.
    Use this when a customer asks to see videos or clips of a product."""

    db = config["configurable"]["db"]
    p, err = await _find_product(db, product_name)
    if err:
        return err

    if not p.media:
        return f"*{p.name}* doesn't have any videos available."

    videos = [item for item in p.media if item.type in ("video", "live_video")]
    if not videos:
        return f"*{p.name}* doesn't have any videos available."

    urls = ",".join(item.url for item in videos)
    caption = f"Videos for *{p.name}* ({len(videos)} clips)"

    return f"[PRODUCT_START]\n{caption}\n[PRODUCT_MEDIA]{urls}[/PRODUCT_MEDIA]\n[PRODUCT_END]"


product_tools = [
    search_products,
    get_product_details,
    get_product_media,
    get_product_images,
    get_product_videos,
]
