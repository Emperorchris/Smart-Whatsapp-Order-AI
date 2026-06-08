from typing import Optional
from decimal import Decimal
import random
import string

from sqlalchemy import select, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
import cloudinary.uploader

from ..db.schemas import product_schema
from ..core import exceptions
from ..db.model import product_model
from ..core.config import CloudinaryConfig


def _extract_public_id(url: str) -> str:
    parts = url.split("/upload/")[-1]
    if parts.startswith("v") and "/" in parts:
        parts = parts.split("/", 1)[1]
    public_id = parts.rsplit(".", 1)[0]
    return public_id


def _delete_cloudinary_files(urls: list[str], resource_type: str = "image"):
    for url in urls:
        public_id = _extract_public_id(url)
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)


def _delete_product_media(product):
    if not product.media:
        return
    for item in product.media:
        resource_type = "video" if item["type"] in ("video", "live_video") else "image"
        _delete_cloudinary_files([item["url"]], resource_type=resource_type)


async def update_media_item_live_status(db: AsyncSession, product_id: str, media_url: str, is_live: bool) -> product_schema.ProductResponse:
    """Toggle the is_live flag on an existing media item by its URL."""
    result = await db.execute(
        select(product_model.Product).filter(product_model.Product.id == product_id)
    )
    product = result.scalars().first()
    if not product:
        raise exceptions.NotFoundException("Product not found.")

    if not product.media:
        raise exceptions.NotFoundException("Product has no media.")

    matching = [m for m in product.media if m.get("url") == media_url]
    if not matching:
        raise exceptions.NotFoundException("Media item not found on this product.")

    def _toggle_type(current_type: str, live: bool) -> str:
        base = current_type.replace("live_", "")  # strip existing live_ prefix
        return f"live_{base}" if live else base

    product.media = [
        {**m, "type": _toggle_type(m["type"], is_live)} if m.get("url") == media_url else m
        for m in product.media
    ]

    await db.commit()
    await db.refresh(product)
    return product_schema.ProductResponse.model_validate(product)


async def delete_product_media_item(db: AsyncSession, product_id: str, media_url: str) -> product_schema.ProductResponse:
    """Remove a single media item from a product by its URL and delete from Cloudinary."""
    result = await db.execute(
        select(product_model.Product).filter(product_model.Product.id == product_id)
    )
    product = result.scalars().first()
    if not product:
        raise exceptions.NotFoundException("Product not found.")

    if not product.media:
        raise exceptions.NotFoundException("Product has no media.")

    matching = [m for m in product.media if m.get("url") == media_url]
    if not matching:
        raise exceptions.NotFoundException("Media item not found on this product.")

    # Delete from Cloudinary
    item = matching[0]
    resource_type = "video" if item["type"] in ("video", "live_video") else "image"
    _delete_cloudinary_files([media_url], resource_type=resource_type)

    # Remove from product media list
    product.media = [m for m in product.media if m.get("url") != media_url]
    await db.commit()
    await db.refresh(product)

    return product_schema.ProductResponse.model_validate(product)


async def upload_media(file, is_live: bool = False) -> dict:
    content = await file.read()
    result = cloudinary.uploader.upload(
        content,
        folder="whatsapp_commerce/products/media",
        resource_type="auto"
    )
    base_type = result["resource_type"]
    media_type = f"live_{base_type}" if is_live else base_type
    return {"url": result["secure_url"], "type": media_type}


async def upload_media_files(files: list, is_live_flags: list[bool] = None) -> list[dict]:
    # Filter out empty UploadFile objects FastAPI injects when no files are submitted
    valid = [(i, f) for i, f in enumerate(files) if getattr(f, "filename", None) and f.filename]
    if not valid:
        return []
    if is_live_flags is None:
        is_live_flags = [False] * len(files)
    return [
        await upload_media(f, is_live=is_live_flags[i] if i < len(is_live_flags) else False)
        for i, f in valid
    ]


async def create_product(db: AsyncSession, product_data: product_schema.ProductSchema, files: list = None, is_live_flags: list[bool] = None) -> product_schema.ProductResponse:
    if product_data.sku:
        result = await db.execute(
            select(product_model.Product).filter(product_model.Product.sku == product_data.sku)
        )
        if result.scalars().first():
            raise exceptions.ConflictException("A product with this SKU already exists.")

    prefix = product_data.name[:4].upper()
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    tracking_id = f"{prefix}-{suffix}"

    media = (await upload_media_files(files, is_live_flags=is_live_flags)) if files else None

    new_product = product_model.Product(
        name=product_data.name,
        tracking_id=tracking_id,
        description=product_data.description,
        price=product_data.price,
        sku=product_data.sku,
        category_id=product_data.category_id,
        media=media,
        tags=product_data.tags,
        is_active=product_data.is_active
    )

    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    return product_schema.ProductResponse.model_validate(new_product)


async def get_product_by_id(db: AsyncSession, product_id: str) -> product_schema.ProductResponse:
    result = await db.execute(
        select(product_model.Product).filter(
            product_model.Product.id == product_id
        )
    )
    product = result.scalars().first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    return product_schema.ProductResponse.model_validate(product)


async def get_all_products(db: AsyncSession, skip: int = 0, limit: int = 50, active_only: bool = True) -> list[product_schema.ProductResponse]:
    query = select(product_model.Product)
    if active_only:
        query = query.filter(product_model.Product.is_active.is_(True))
    result = await db.execute(query.offset(skip).limit(limit))
    products = result.scalars().all()
    return [product_schema.ProductResponse.model_validate(p) for p in products]


async def get_product_names_paginated(
    db: AsyncSession, page: int = 1, page_size: int = 20, active_only: bool = True
) -> dict:
    """Fetch only product names and prices — lightweight, no media/variants/description.

    Returns:
        {
            "products": [{"id": "...", "name": "...", "price": 18500.00}, ...],
            "page": 1,
            "page_size": 20,
            "total": 30,
            "has_more": True,
        }
    """
    from sqlalchemy import func

    query = select(product_model.Product.id, product_model.Product.name, product_model.Product.price)
    count_query = select(func.count(product_model.Product.id))

    if active_only:
        query = query.filter(product_model.Product.is_active.is_(True))
        count_query = count_query.filter(product_model.Product.is_active.is_(True))

    # Total count
    total = (await db.execute(count_query)).scalar() or 0

    # Paginated results
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(product_model.Product.name).offset(offset).limit(page_size)
    )
    rows = result.all()

    products = [
        {"id": str(row.id), "name": row.name, "price": float(row.price)}
        for row in rows
    ]

    return {
        "products": products,
        "page": page,
        "page_size": page_size,
        "total": total,
        "has_more": (offset + page_size) < total,
    }


async def get_product_by_sku(db: AsyncSession, sku: str) -> product_schema.ProductResponse:
    result = await db.execute(
        select(product_model.Product).filter(
            product_model.Product.sku == sku,
            product_model.Product.is_active.is_(True)
        )
    )
    product = result.scalars().first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    return product_schema.ProductResponse.model_validate(product)


async def update_product(db: AsyncSession, product_id: str, product_data: product_schema.ProductSchema, files: list = None, is_live_flags: list[bool] = None) -> product_schema.ProductResponse:
    result = await db.execute(
        select(product_model.Product).filter(product_model.Product.id == product_id)
    )
    product = result.scalars().first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    if product_data.sku:
        dup_result = await db.execute(
            select(product_model.Product).filter(
                product_model.Product.sku == product_data.sku,
                product_model.Product.id != product_id
            )
        )
        if dup_result.scalars().first():
            raise exceptions.ConflictException("SKU is already taken by another product.")

    existing_media = product.media or []
    new_media = await upload_media_files(files or [], is_live_flags=is_live_flags)
    # Spread into a new list so SQLAlchemy detects the JSON column mutation
    product.media = [*existing_media, *new_media]

    product.name = product_data.name
    product.description = product_data.description
    product.price = product_data.price
    product.sku = product_data.sku
    product.category_id = product_data.category_id
    product.tags = product_data.tags
    product.is_active = product_data.is_active

    await db.commit()
    await db.refresh(product)

    return product_schema.ProductResponse.model_validate(product)


async def search_products(
    db: AsyncSession,
    name: Optional[str] = None,
    description: Optional[str] = None,
    category_id: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    is_active: Optional[bool] = None,
    sku: Optional[str] = None,
    tag: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
) -> list[product_schema.ProductResponse]:
    query = select(product_model.Product)

    # If active_only is set and caller didn't explicitly pass is_active, filter to active
    if active_only and is_active is None:
        query = query.filter(product_model.Product.is_active.is_(True))
    elif is_active is not None:
        query = query.filter(product_model.Product.is_active == is_active)

    if name:
        query = query.filter(product_model.Product.name.ilike(f"%{name}%"))
    if category_id:
        query = query.filter(product_model.Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(product_model.Product.price >= min_price)
    if max_price is not None:
        query = query.filter(product_model.Product.price <= max_price)
    if sku:
        query = query.filter(product_model.Product.sku == sku)
    if description:
        query = query.filter(product_model.Product.description.ilike(f"%{description}%"))
    if tag:
        query = query.filter(
            cast(product_model.Product.tags, String).ilike(f"%{tag}%")
        )

    result = await db.execute(query.offset(skip).limit(limit))
    products = result.scalars().all()
    return [product_schema.ProductResponse.model_validate(p) for p in products]


async def delete_product(db: AsyncSession, product_id: str, hard_delete: bool = False):
    result = await db.execute(
        select(product_model.Product).filter(product_model.Product.id == product_id)
    )
    product = result.scalars().first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    if hard_delete:
        _delete_product_media(product)
        await db.delete(product)
    else:
        product.is_active = False

    await db.commit()
