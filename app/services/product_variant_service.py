from ..db.schemas import product_variant_schema
from ..core import exceptions
from ..db.model import product_variant_model, product_model
from sqlalchemy.orm import Session


def create_variant(db: Session, data: product_variant_schema.ProductVariantSchema) -> product_variant_schema.ProductVariantResponse:
    product = db.query(product_model.Product).filter(
        product_model.Product.id == data.product_id
    ).first()
    if not product:
        raise exceptions.NotFoundException("Product not found.")

    existing = db.query(product_variant_model.ProductVariant).filter(
        product_variant_model.ProductVariant.sku == data.sku
    ).first()
    if existing:
        raise exceptions.ConflictException("A variant with this SKU already exists.")

    new_variant = product_variant_model.ProductVariant(
        product_id=data.product_id,
        sku=data.sku,
        attributes=data.attributes,
        price=data.price,
        inventory_quantity=data.inventory_quantity,
        low_stock_threshold=data.low_stock_threshold,
        is_active=data.is_active
    )

    db.add(new_variant)
    db.commit()
    db.refresh(new_variant)

    return product_variant_schema.ProductVariantResponse.model_validate(new_variant)


def get_variant_by_id(db: Session, variant_id: str) -> product_variant_schema.ProductVariantResponse:
    variant = db.query(product_variant_model.ProductVariant).filter(
        product_variant_model.ProductVariant.id == variant_id,
        product_variant_model.ProductVariant.is_active.is_(True)).first()

    if not variant:
        raise exceptions.NotFoundException("Product variant not found.")

    return product_variant_schema.ProductVariantResponse.model_validate(variant)


def get_variants_by_product_id(db: Session, product_id: str) -> list[product_variant_schema.ProductVariantResponse]:
    variants = db.query(product_variant_model.ProductVariant).filter(
        product_variant_model.ProductVariant.product_id == product_id,
        product_variant_model.ProductVariant.is_active.is_(True)).all()
    return [product_variant_schema.ProductVariantResponse.model_validate(v) for v in variants]


def get_variant_by_sku(db: Session, sku: str) -> product_variant_schema.ProductVariantResponse:
    variant = db.query(product_variant_model.ProductVariant).filter(
        product_variant_model.ProductVariant.sku == sku,
        product_variant_model.ProductVariant.is_active.is_(True)).first()

    if not variant:
        raise exceptions.NotFoundException("Product variant not found.")

    return product_variant_schema.ProductVariantResponse.model_validate(variant)


def get_all_variants(db: Session) -> list[product_variant_schema.ProductVariantResponse]:
    variants = db.query(product_variant_model.ProductVariant).filter(
        product_variant_model.ProductVariant.is_active.is_(True)).all()
    return [product_variant_schema.ProductVariantResponse.model_validate(v) for v in variants]


def update_variant(db: Session, variant_id: str, data: product_variant_schema.ProductVariantSchema) -> product_variant_schema.ProductVariantResponse:
    variant = db.query(product_variant_model.ProductVariant).filter(
        product_variant_model.ProductVariant.id == variant_id).first()

    if not variant:
        raise exceptions.NotFoundException("Product variant not found.")

    is_sku_taken = db.query(product_variant_model.ProductVariant).filter(
        product_variant_model.ProductVariant.sku == data.sku,
        product_variant_model.ProductVariant.id != variant_id
    ).first()
    if is_sku_taken:
        raise exceptions.ConflictException("SKU is already taken by another variant.")

    variant.product_id = data.product_id
    variant.sku = data.sku
    variant.attributes = data.attributes
    variant.price = data.price
    variant.inventory_quantity = data.inventory_quantity
    variant.low_stock_threshold = data.low_stock_threshold
    variant.is_active = data.is_active

    db.commit()
    db.refresh(variant)

    return product_variant_schema.ProductVariantResponse.model_validate(variant)


def delete_variant(db: Session, variant_id: str):
    variant = db.query(product_variant_model.ProductVariant).filter(
        product_variant_model.ProductVariant.id == variant_id).first()

    if not variant:
        raise exceptions.NotFoundException("Product variant not found.")

    db.delete(variant)
    db.commit()
