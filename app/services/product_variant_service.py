from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import product_variant_schema
from ..core import exceptions
from ..db.model import product_variant_model, product_model


async def create_variant(
    db: AsyncSession, data: product_variant_schema.ProductVariantSchema
) -> product_variant_schema.ProductVariantResponse:
    result = await db.execute(
        select(product_model.Product).filter(product_model.Product.id == data.product_id)
    )
    if not result.scalars().first():
        raise exceptions.NotFoundException("Product not found.")

    new_variant = product_variant_model.ProductVariant(
        product_id=data.product_id,
        attributes=data.attributes,
        product_variant_price=data.product_variant_price,
        inventory_quantity=data.inventory_quantity,
        low_stock_threshold=data.low_stock_threshold,
        is_active=data.is_active,
    )

    db.add(new_variant)
    await db.commit()
    await db.refresh(new_variant)

    return product_variant_schema.ProductVariantResponse.model_validate(new_variant)


async def get_variant_by_id(
    db: AsyncSession, variant_id: str
) -> product_variant_schema.ProductVariantResponse:
    result = await db.execute(
        select(product_variant_model.ProductVariant).filter(
            product_variant_model.ProductVariant.id == variant_id,
            product_variant_model.ProductVariant.is_active.is_(True),
        )
    )
    variant = result.scalars().first()

    if not variant:
        raise exceptions.NotFoundException("Product variant not found.")

    return product_variant_schema.ProductVariantResponse.model_validate(variant)


async def get_variants_by_product_id(
    db: AsyncSession, product_id: str
) -> list[product_variant_schema.ProductVariantResponse]:
    result = await db.execute(
        select(product_variant_model.ProductVariant).filter(
            product_variant_model.ProductVariant.product_id == product_id,
            product_variant_model.ProductVariant.is_active.is_(True),
        )
    )
    variants = result.scalars().all()
    return [
        product_variant_schema.ProductVariantResponse.model_validate(v)
        for v in variants
    ]


async def get_variant_by_sku(
    db: AsyncSession, sku: str
) -> product_variant_schema.ProductVariantResponse:
    result = await db.execute(
        select(product_variant_model.ProductVariant).filter(
            product_variant_model.ProductVariant.sku == sku,
            product_variant_model.ProductVariant.is_active.is_(True),
        )
    )
    variant = result.scalars().first()

    if not variant:
        raise exceptions.NotFoundException("Product variant not found.")

    return product_variant_schema.ProductVariantResponse.model_validate(variant)


async def get_all_variants(
    db: AsyncSession,
) -> list[product_variant_schema.ProductVariantResponse]:
    result = await db.execute(
        select(product_variant_model.ProductVariant).filter(
            product_variant_model.ProductVariant.is_active.is_(True)
        )
    )
    variants = result.scalars().all()
    return [
        product_variant_schema.ProductVariantResponse.model_validate(v)
        for v in variants
    ]


async def update_variant(
    db: AsyncSession, variant_id: str, data: product_variant_schema.ProductVariantSchema
) -> product_variant_schema.ProductVariantResponse:
    result = await db.execute(
        select(product_variant_model.ProductVariant).filter(
            product_variant_model.ProductVariant.id == variant_id
        )
    )
    variant = result.scalars().first()

    if not variant:
        raise exceptions.NotFoundException("Product variant not found.")

    variant.product_id = data.product_id
    variant.attributes = data.attributes
    variant.product_variant_price = data.product_variant_price
    variant.inventory_quantity = data.inventory_quantity
    variant.low_stock_threshold = data.low_stock_threshold
    variant.is_active = data.is_active

    await db.commit()
    await db.refresh(variant)

    return product_variant_schema.ProductVariantResponse.model_validate(variant)


async def delete_variant(db: AsyncSession, variant_id: str):
    result = await db.execute(
        select(product_variant_model.ProductVariant).filter(
            product_variant_model.ProductVariant.id == variant_id
        )
    )
    variant = result.scalars().first()

    if not variant:
        raise exceptions.NotFoundException("Product variant not found.")

    await db.delete(variant)
    await db.commit()
