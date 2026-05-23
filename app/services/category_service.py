from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import category_schema
from ..core import exceptions
from ..db.model import category_model


async def create_category(db: AsyncSession, data: category_schema.CategorySchema) -> category_schema.CategoryResponse:
    if data.parent_id:
        result = await db.execute(
            select(category_model.Category).filter(category_model.Category.id == data.parent_id)
        )
        if not result.scalars().first():
            raise exceptions.NotFoundException("Parent category not found.")

    new_category = category_model.Category(
        name=data.name,
        description=data.description,
        parent_id=data.parent_id,
        is_active=data.is_active
    )

    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)

    return category_schema.CategoryResponse.model_validate(new_category)


async def get_category_by_id(db: AsyncSession, category_id: str) -> category_schema.CategoryResponse:
    result = await db.execute(
        select(category_model.Category).filter(
            category_model.Category.id == category_id,
            category_model.Category.is_active.is_(True)
        )
    )
    category = result.scalars().first()

    if not category:
        raise exceptions.NotFoundException("Category not found.")

    return category_schema.CategoryResponse.model_validate(category)


async def get_all_categories(db: AsyncSession) -> list[category_schema.CategoryResponse]:
    result = await db.execute(
        select(category_model.Category).filter(category_model.Category.is_active.is_(True))
    )
    categories = result.scalars().all()
    return [category_schema.CategoryResponse.model_validate(c) for c in categories]


async def get_subcategories(db: AsyncSession, parent_id: str) -> list[category_schema.CategoryResponse]:
    result = await db.execute(
        select(category_model.Category).filter(
            category_model.Category.parent_id == parent_id,
            category_model.Category.is_active.is_(True)
        )
    )
    categories = result.scalars().all()
    return [category_schema.CategoryResponse.model_validate(c) for c in categories]


async def get_root_categories(db: AsyncSession) -> list[category_schema.CategoryResponse]:
    result = await db.execute(
        select(category_model.Category).filter(
            category_model.Category.parent_id == None,
            category_model.Category.is_active.is_(True)
        )
    )
    categories = result.scalars().all()
    return [category_schema.CategoryResponse.model_validate(c) for c in categories]


async def update_category(db: AsyncSession, category_id: str, data: category_schema.CategorySchema) -> category_schema.CategoryResponse:
    result = await db.execute(
        select(category_model.Category).filter(category_model.Category.id == category_id)
    )
    category = result.scalars().first()

    if not category:
        raise exceptions.NotFoundException("Category not found.")

    if data.parent_id:
        if str(data.parent_id) == str(category_id):
            raise exceptions.BadRequestException("A category cannot be its own parent.")
        parent_result = await db.execute(
            select(category_model.Category).filter(category_model.Category.id == data.parent_id)
        )
        if not parent_result.scalars().first():
            raise exceptions.NotFoundException("Parent category not found.")

    category.name = data.name
    category.description = data.description
    category.parent_id = data.parent_id
    category.is_active = data.is_active

    await db.commit()
    await db.refresh(category)

    return category_schema.CategoryResponse.model_validate(category)


async def delete_category(db: AsyncSession, category_id: str):
    result = await db.execute(
        select(category_model.Category).filter(category_model.Category.id == category_id)
    )
    category = result.scalars().first()

    if not category:
        raise exceptions.NotFoundException("Category not found.")

    await db.delete(category)
    await db.commit()
