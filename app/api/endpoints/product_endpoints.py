from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Query
from ...core.dependencies import DBSession
from ...services import product_service
from ...db.schemas import product_schema

product_router = APIRouter(prefix="/products", tags=["Products"])


@product_router.post("/", response_model=product_schema.ProductResponse)
def create_product(product_data: product_schema.ProductSchema, db: DBSession):
    return product_service.create_product(db, product_data)


@product_router.get("/", response_model=list[product_schema.ProductResponse])
def get_all_products(db: DBSession):
    return product_service.get_all_products(db)


@product_router.get("/search", response_model=list[product_schema.ProductResponse])
def search_products(
    db: DBSession,
    name: Optional[str] = Query(None, description="Search by product name"),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    min_price: Optional[Decimal] = Query(None, description="Minimum price"),
    max_price: Optional[Decimal] = Query(None, description="Maximum price"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    return product_service.search_products(db, name, category_id, min_price, max_price, is_active)


@product_router.get("/{product_id}", response_model=product_schema.ProductResponse)
def get_product(product_id: str, db: DBSession):
    return product_service.get_product_by_id(db, product_id)


@product_router.get("/sku/{sku}", response_model=product_schema.ProductResponse)
def get_product_by_sku(sku: str, db: DBSession):
    return product_service.get_product_by_sku(db, sku)


@product_router.put("/{product_id}", response_model=product_schema.ProductResponse)
def update_product(product_id: str, product_data: product_schema.ProductSchema, db: DBSession):
    return product_service.update_product(db, product_id, product_data)


@product_router.delete("/{product_id}", status_code=204)
def delete_product(product_id: str, db: DBSession):
    product_service.delete_product(db, product_id)
