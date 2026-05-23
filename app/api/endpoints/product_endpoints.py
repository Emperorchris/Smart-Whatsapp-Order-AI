from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Query, Form, UploadFile, File
from ...core.dependencies import DBSession
from ...services import product_service
from ...db.schemas import product_schema

product_router = APIRouter(prefix="/products", tags=["Products"])


@product_router.post("/", response_model=product_schema.ProductResponse)
async def create_product(
    db: DBSession,
    name: str = Form(...),
    price: Decimal = Form(...),
    description: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    is_active: bool = Form(True),
    is_live: bool = Form(False),
    files: list[UploadFile] = File(default=[]),
):
    product_data = product_schema.ProductSchema(
        name=name,
        price=price,
        description=description,
        sku=sku,
        category_id=category_id,
        is_active=is_active,
    )
    return await product_service.create_product(db, product_data, files=files, is_live=is_live)


@product_router.get("/", response_model=list[product_schema.ProductResponse])
async def get_all_products(
    db: DBSession,
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max products to return"),
):
    return await product_service.get_all_products(db, skip=skip, limit=limit)


@product_router.get("/search", response_model=list[product_schema.ProductResponse])
async def search_products(
    db: DBSession,
    name: Optional[str] = Query(None, description="Search by product name"),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    min_price: Optional[Decimal] = Query(None, description="Minimum price"),
    max_price: Optional[Decimal] = Query(None, description="Maximum price"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max products to return"),
):
    return await product_service.search_products(
        db, name=name, category_id=category_id, min_price=min_price,
        max_price=max_price, is_active=is_active, skip=skip, limit=limit,
    )


@product_router.get("/{product_id}", response_model=product_schema.ProductResponse)
async def get_product(product_id: str, db: DBSession):
    return await product_service.get_product_by_id(db, product_id)


@product_router.get("/sku/{sku}", response_model=product_schema.ProductResponse)
async def get_product_by_sku(sku: str, db: DBSession):
    return await product_service.get_product_by_sku(db, sku)


@product_router.put("/{product_id}", response_model=product_schema.ProductResponse)
async def update_product(
    product_id: str,
    db: DBSession,
    name: str = Form(...),
    price: Decimal = Form(...),
    description: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    is_active: bool = Form(True),
    is_live: bool = Form(False),
    files: list[UploadFile] = File(default=[]),
):
    product_data = product_schema.ProductSchema(
        name=name,
        price=price,
        description=description,
        sku=sku,
        category_id=category_id,
        is_active=is_active,
    )
    return await product_service.update_product(db, product_id, product_data, files=files, is_live=is_live)


@product_router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str, db: DBSession):
    await product_service.delete_product(db, product_id)
