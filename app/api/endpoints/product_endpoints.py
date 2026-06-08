import json
from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Query, Form, UploadFile, File
from pydantic import BaseModel
from ...core.dependencies import DBSession
from ...services import product_service
from ...services.auth_service import CurrentStaff, AdminOnly
from ...db.schemas import product_schema

product_router = APIRouter(prefix="/products", tags=["Products"])


@product_router.post("/", response_model=product_schema.ProductResponse)
async def create_product(
    db: DBSession,
    _: AdminOnly,
    name: str = Form(...),
    price: Decimal = Form(...),
    description: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    is_active: bool = Form(True),
    tags: Optional[str] = Form(None, description='JSON array of tags e.g. ["dress", "ankara", "clothes"]'),
    files: list[UploadFile] = File(default=[]),
    is_live: list[str] = Form(default=[], description='One "true"/"false" per file in the same order as files'),
):
    parsed_tags = json.loads(tags) if tags else None
    is_live_flags = [v.strip().lower() == "true" for v in is_live] if is_live else None
    product_data = product_schema.ProductSchema(
        name=name,
        price=price,
        description=description,
        sku=sku,
        category_id=category_id,
        tags=parsed_tags,
        is_active=is_active,
    )
    return await product_service.create_product(db, product_data, files=files, is_live_flags=is_live_flags)


@product_router.get("/", response_model=list[product_schema.ProductResponse])
async def get_all_products(
    db: DBSession,
    _: CurrentStaff,
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max products to return"),
):
    return await product_service.get_all_products(db, skip=skip, limit=limit, active_only=False)


@product_router.get("/search", response_model=list[product_schema.ProductResponse])
async def search_products(
    db: DBSession,
    _: CurrentStaff,
    name: Optional[str] = Query(None, description="Search by product name"),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    min_price: Optional[Decimal] = Query(None, description="Minimum price"),
    max_price: Optional[Decimal] = Query(None, description="Maximum price"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    tag: Optional[str] = Query(None, description="Search by tag"),
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max products to return"),
):
    return await product_service.search_products(
        db, name=name, category_id=category_id, min_price=min_price,
        max_price=max_price, is_active=is_active, tag=tag, skip=skip, limit=limit,
        active_only=False,
    )


@product_router.get("/{product_id}", response_model=product_schema.ProductResponse)
async def get_product(product_id: str, db: DBSession, _: CurrentStaff):
    return await product_service.get_product_by_id(db, product_id)


@product_router.get("/sku/{sku}", response_model=product_schema.ProductResponse)
async def get_product_by_sku(sku: str, db: DBSession, _: CurrentStaff):
    return await product_service.get_product_by_sku(db, sku)


@product_router.put("/{product_id}", response_model=product_schema.ProductResponse)
async def update_product(
    product_id: str,
    db: DBSession,
    _: AdminOnly,
    name: str = Form(...),
    price: Decimal = Form(...),
    description: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    is_active: bool = Form(True),
    tags: Optional[str] = Form(None, description='JSON array of tags e.g. ["dress", "ankara", "clothes"]'),
    files: list[UploadFile] = File(default=[]),
    is_live: list[str] = Form(default=[], description='One "true"/"false" per file in the same order as files'),
):
    parsed_tags = json.loads(tags) if tags else None
    is_live_flags = [v.strip().lower() == "true" for v in is_live] if is_live else None
    product_data = product_schema.ProductSchema(
        name=name,
        price=price,
        description=description,
        sku=sku,
        category_id=category_id,
        tags=parsed_tags,
        is_active=is_active,
    )
    return await product_service.update_product(db, product_id, product_data, files=files, is_live_flags=is_live_flags)


class DeleteMediaBody(BaseModel):
    media_url: str


class UpdateMediaLiveBody(BaseModel):
    media_url: str
    is_live: bool


@product_router.patch("/{product_id}/media", response_model=product_schema.ProductResponse)
async def update_media_live_status(product_id: str, body: UpdateMediaLiveBody, db: DBSession, _: AdminOnly):
    return await product_service.update_media_item_live_status(db, product_id, body.media_url, body.is_live)


@product_router.delete("/{product_id}/media", response_model=product_schema.ProductResponse)
async def delete_product_media(product_id: str, body: DeleteMediaBody, db: DBSession, _: AdminOnly):
    return await product_service.delete_product_media_item(db, product_id, body.media_url)


@product_router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str, db: DBSession, _: AdminOnly):
    await product_service.delete_product(db, product_id)
