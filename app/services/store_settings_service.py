from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.model.store_settings_model import StoreSettings
from ..db.schemas import store_settings_schema
from ..core import exceptions


async def get_all_settings(db: AsyncSession) -> list[store_settings_schema.StoreSettingResponse]:
    result = await db.execute(select(StoreSettings).order_by(StoreSettings.key))
    return [store_settings_schema.StoreSettingResponse.model_validate(s) for s in result.scalars().all()]


async def get_setting(db: AsyncSession, key: str) -> store_settings_schema.StoreSettingResponse:
    result = await db.execute(select(StoreSettings).where(StoreSettings.key == key))
    setting = result.scalars().first()
    if not setting:
        raise exceptions.NotFoundException(f"Setting '{key}' not found.")
    return store_settings_schema.StoreSettingResponse.model_validate(setting)


async def upsert_setting(
    db: AsyncSession,
    data: store_settings_schema.StoreSettingSchema,
) -> store_settings_schema.StoreSettingResponse:
    result = await db.execute(select(StoreSettings).where(StoreSettings.key == data.key))
    setting = result.scalars().first()

    if setting:
        setting.value = data.value
        if data.description is not None:
            setting.description = data.description
    else:
        setting = StoreSettings(key=data.key, value=data.value, description=data.description)
        db.add(setting)

    await db.commit()
    await db.refresh(setting)
    return store_settings_schema.StoreSettingResponse.model_validate(setting)


async def bulk_upsert(
    db: AsyncSession,
    bulk: store_settings_schema.StoreSettingsBulkUpdate,
) -> list[store_settings_schema.StoreSettingResponse]:
    results = []
    for item in bulk.settings:
        results.append(await upsert_setting(db, item))
    return results


async def delete_setting(db: AsyncSession, key: str):
    result = await db.execute(select(StoreSettings).where(StoreSettings.key == key))
    setting = result.scalars().first()
    if not setting:
        raise exceptions.NotFoundException(f"Setting '{key}' not found.")
    await db.delete(setting)
    await db.commit()
