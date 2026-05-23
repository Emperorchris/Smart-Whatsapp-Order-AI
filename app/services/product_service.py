from typing import Optional
from decimal import Decimal
import random
import string

from sqlalchemy import select
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


def upload_media(file, is_live: bool = False) -> dict:
    result = cloudinary.uploader.upload(
        file,
        folder="whatsapp_commerce/products/media",
        resource_type="auto"
    )
    base_type = result["resource_type"]
    media_type = f"live_{base_type}" if is_live else base_type
    return {"url": result["secure_url"], "type": media_type}


def upload_media_files(files: list, is_live: bool = False) -> list[dict]:
    return [upload_media(f, is_live=is_live) for f in files]


async def create_product(db: AsyncSession, product_data: product_schema.ProductSchema, files: list = None, is_live: bool = False) -> product_schema.ProductResponse:
    if product_data.sku:
        result = await db.execute(
            select(product_model.Product).filter(product_model.Product.sku == product_data.sku)
        )
        if result.scalars().first():
            raise exceptions.ConflictException("A product with this SKU already exists.")

    prefix = product_data.name[:4].upper()
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    tracking_id = f"{prefix}-{suffix}"

    media = upload_media_files(files, is_live=is_live) if files else None

    new_product = product_model.Product(
        name=product_data.name,
        tracking_id=tracking_id,
        description=product_data.description,
        price=product_data.price,
        sku=product_data.sku,
        category_id=product_data.category_id,
        media=media,
        is_active=product_data.is_active
    )

    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    return product_schema.ProductResponse.model_validate(new_product)


async def get_product_by_id(db: AsyncSession, product_id: str) -> product_schema.ProductResponse:
    result = await db.execute(
        select(product_model.Product).filter(
            product_model.Product.id == product_id,
            product_model.Product.is_active.is_(True)
        )
    )
    product = result.scalars().first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    return product_schema.ProductResponse.model_validate(product)


async def get_all_products(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[product_schema.ProductResponse]:
    result = await db.execute(
        select(product_model.Product).filter(
            product_model.Product.is_active.is_(True)
        ).offset(skip).limit(limit)
    )
    products = result.scalars().all()
    return [product_schema.ProductResponse.model_validate(p) for p in products]


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


async def update_product(db: AsyncSession, product_id: str, product_data: product_schema.ProductSchema, files: list = None, is_live: bool = False) -> product_schema.ProductResponse:
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

    if files and product.media:
        _delete_product_media(product)

    media = upload_media_files(files, is_live=is_live) if files else product.media

    product.name = product_data.name
    product.description = product_data.description
    product.price = product_data.price
    product.sku = product_data.sku
    product.category_id = product_data.category_id
    product.media = media
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
    skip: int = 0,
    limit: int = 50,
) -> list[product_schema.ProductResponse]:
    query = select(product_model.Product)

    if name:
        query = query.filter(product_model.Product.name.ilike(f"%{name}%"))
    if category_id:
        query = query.filter(product_model.Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(product_model.Product.price >= min_price)
    if max_price is not None:
        query = query.filter(product_model.Product.price <= max_price)
    if is_active is not None:
        query = query.filter(product_model.Product.is_active == is_active)
    if sku:
        query = query.filter(product_model.Product.sku == sku)
    if description:
        query = query.filter(product_model.Product.description.ilike(f"%{description}%"))

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
