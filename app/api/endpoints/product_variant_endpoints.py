from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import product_variant_service
from ...db.schemas import product_variant_schema

variant_router = APIRouter(prefix="/product-variants", tags=["Product Variants"])


@variant_router.post("/", response_model=product_variant_schema.ProductVariantResponse)
def create_variant(data: product_variant_schema.ProductVariantSchema, db: DBSession):
    return product_variant_service.create_variant(db, data)


@variant_router.get("/", response_model=list[product_variant_schema.ProductVariantResponse])
def get_all_variants(db: DBSession):
    return product_variant_service.get_all_variants(db)


@variant_router.get("/{variant_id}", response_model=product_variant_schema.ProductVariantResponse)
def get_variant(variant_id: str, db: DBSession):
    return product_variant_service.get_variant_by_id(db, variant_id)


@variant_router.get("/sku/{sku}", response_model=product_variant_schema.ProductVariantResponse)
def get_variant_by_sku(sku: str, db: DBSession):
    return product_variant_service.get_variant_by_sku(db, sku)


@variant_router.get("/product/{product_id}", response_model=list[product_variant_schema.ProductVariantResponse])
def get_variants_by_product(product_id: str, db: DBSession):
    return product_variant_service.get_variants_by_product_id(db, product_id)


@variant_router.put("/{variant_id}", response_model=product_variant_schema.ProductVariantResponse)
def update_variant(variant_id: str, data: product_variant_schema.ProductVariantSchema, db: DBSession):
    return product_variant_service.update_variant(db, variant_id, data)


@variant_router.delete("/{variant_id}", status_code=204)
def delete_variant(variant_id: str, db: DBSession):
    product_variant_service.delete_variant(db, variant_id)
