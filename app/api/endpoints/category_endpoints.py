from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import category_service
from ...db.schemas import category_schema

category_router = APIRouter(prefix="/categories", tags=["Categories"])


@category_router.post("/", response_model=category_schema.CategoryResponse)
def create_category(data: category_schema.CategorySchema, db: DBSession):
    return category_service.create_category(db, data)


@category_router.get("/", response_model=list[category_schema.CategoryResponse])
def get_all_categories(db: DBSession):
    return category_service.get_all_categories(db)


@category_router.get("/root", response_model=list[category_schema.CategoryResponse])
def get_root_categories(db: DBSession):
    return category_service.get_root_categories(db)


@category_router.get("/{category_id}", response_model=category_schema.CategoryResponse)
def get_category(category_id: str, db: DBSession):
    return category_service.get_category_by_id(db, category_id)


@category_router.get("/{category_id}/subcategories", response_model=list[category_schema.CategoryResponse])
def get_subcategories(category_id: str, db: DBSession):
    return category_service.get_subcategories(db, category_id)


@category_router.put("/{category_id}", response_model=category_schema.CategoryResponse)
def update_category(category_id: str, data: category_schema.CategorySchema, db: DBSession):
    return category_service.update_category(db, category_id, data)


@category_router.delete("/{category_id}", status_code=204)
def delete_category(category_id: str, db: DBSession):
    category_service.delete_category(db, category_id)
