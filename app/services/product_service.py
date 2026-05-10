from ..db.schemas import product_schema
from ..core import exceptions
from ..db.model import product_model
from sqlalchemy.orm import Session


def create_product(db: Session, product_data: product_schema.ProductSchema) -> product_schema.ProductResponse:
    if product_data.sku:
        existing = db.query(product_model.Product).filter(
            product_model.Product.sku == product_data.sku
        ).first()
        if existing:
            raise exceptions.ConflictException("A product with this SKU already exists.")

    new_product = product_model.Product(
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        sku=product_data.sku,
        category=product_data.category,
        image_urls=product_data.image_urls,
        is_active=product_data.is_active
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return product_schema.ProductResponse.model_validate(new_product)


def get_product_by_id(db: Session, product_id: str) -> product_schema.ProductResponse:
    product = db.query(product_model.Product).filter(
        product_model.Product.id == product_id).first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    return product_schema.ProductResponse.model_validate(product)


def get_all_products(db: Session) -> list[product_schema.ProductResponse]:
    products = db.query(product_model.Product).all()
    return [product_schema.ProductResponse.model_validate(p) for p in products]


def get_product_by_sku(db: Session, sku: str) -> product_schema.ProductResponse:
    product = db.query(product_model.Product).filter(
        product_model.Product.sku == sku).first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    return product_schema.ProductResponse.model_validate(product)


def update_product(db: Session, product_id: str, product_data: product_schema.ProductSchema) -> product_schema.ProductResponse:
    product = db.query(product_model.Product).filter(
        product_model.Product.id == product_id).first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    if product_data.sku:
        is_sku_taken = db.query(product_model.Product).filter(
            product_model.Product.sku == product_data.sku,
            product_model.Product.id != product_id
        ).first()
        if is_sku_taken:
            raise exceptions.ConflictException("SKU is already taken by another product.")

    product.name = product_data.name
    product.description = product_data.description
    product.price = product_data.price
    product.sku = product_data.sku
    product.category = product_data.category
    product.image_urls = product_data.image_urls
    product.is_active = product_data.is_active

    db.commit()
    db.refresh(product)

    return product_schema.ProductResponse.model_validate(product)


def delete_product(db: Session, product_id: str):
    product = db.query(product_model.Product).filter(
        product_model.Product.id == product_id).first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    db.delete(product)
    db.commit()
