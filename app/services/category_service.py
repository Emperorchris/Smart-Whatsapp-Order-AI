from ..db.schemas import category_schema
from ..core import exceptions
from ..db.model import category_model
from sqlalchemy.orm import Session


def create_category(db: Session, data: category_schema.CategorySchema) -> category_schema.CategoryResponse:
    if data.parent_id:
        parent = db.query(category_model.Category).filter(
            category_model.Category.id == data.parent_id
        ).first()
        if not parent:
            raise exceptions.NotFoundException("Parent category not found.")

    new_category = category_model.Category(
        name=data.name,
        description=data.description,
        parent_id=data.parent_id,
        is_active=data.is_active
    )

    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    return category_schema.CategoryResponse.model_validate(new_category)


def get_category_by_id(db: Session, category_id: str) -> category_schema.CategoryResponse:
    category = db.query(category_model.Category).filter(
        category_model.Category.id == category_id,
        category_model.Category.is_active.is_(True)).first()

    if not category:
        raise exceptions.NotFoundException("Category not found.")

    return category_schema.CategoryResponse.model_validate(category)


def get_all_categories(db: Session) -> list[category_schema.CategoryResponse]:
    categories = db.query(category_model.Category).filter(
        category_model.Category.is_active.is_(True)).all()
    return [category_schema.CategoryResponse.model_validate(c) for c in categories]


def get_subcategories(db: Session, parent_id: str) -> list[category_schema.CategoryResponse]:
    categories = db.query(category_model.Category).filter(
        category_model.Category.parent_id == parent_id,
        category_model.Category.is_active.is_(True)).all()
    return [category_schema.CategoryResponse.model_validate(c) for c in categories]


def get_root_categories(db: Session) -> list[category_schema.CategoryResponse]:
    categories = db.query(category_model.Category).filter(
        category_model.Category.parent_id == None,
        category_model.Category.is_active.is_(True)).all()
    return [category_schema.CategoryResponse.model_validate(c) for c in categories]


def update_category(db: Session, category_id: str, data: category_schema.CategorySchema) -> category_schema.CategoryResponse:
    category = db.query(category_model.Category).filter(
        category_model.Category.id == category_id).first()

    if not category:
        raise exceptions.NotFoundException("Category not found.")

    if data.parent_id:
        if str(data.parent_id) == str(category_id):
            raise exceptions.BadRequestException("A category cannot be its own parent.")
        parent = db.query(category_model.Category).filter(
            category_model.Category.id == data.parent_id
        ).first()
        if not parent:
            raise exceptions.NotFoundException("Parent category not found.")

    category.name = data.name
    category.description = data.description
    category.parent_id = data.parent_id
    category.is_active = data.is_active

    db.commit()
    db.refresh(category)

    return category_schema.CategoryResponse.model_validate(category)


def delete_category(db: Session, category_id: str):
    category = db.query(category_model.Category).filter(
        category_model.Category.id == category_id).first()

    if not category:
        raise exceptions.NotFoundException("Category not found.")

    db.delete(category)
    db.commit()
