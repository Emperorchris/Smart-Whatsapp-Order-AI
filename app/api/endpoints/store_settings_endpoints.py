from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import store_settings_service
from ...db.schemas import store_settings_schema

settings_router = APIRouter(prefix="/settings", tags=["Store Settings"])


@settings_router.get("/", response_model=list[store_settings_schema.StoreSettingResponse])
async def get_all_settings(db: DBSession):
    return await store_settings_service.get_all_settings(db)


@settings_router.get("/{key}", response_model=store_settings_schema.StoreSettingResponse)
async def get_setting(key: str, db: DBSession):
    return await store_settings_service.get_setting(db, key)


@settings_router.put("/", response_model=store_settings_schema.StoreSettingResponse)
async def upsert_setting(data: store_settings_schema.StoreSettingSchema, db: DBSession):
    return await store_settings_service.upsert_setting(db, data)


@settings_router.put("/bulk", response_model=list[store_settings_schema.StoreSettingResponse])
async def bulk_upsert(data: store_settings_schema.StoreSettingsBulkUpdate, db: DBSession):
    return await store_settings_service.bulk_upsert(db, data)


@settings_router.delete("/{key}", status_code=204)
async def delete_setting(key: str, db: DBSession):
    await store_settings_service.delete_setting(db, key)
