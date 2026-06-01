from fastapi import APIRouter, Query
from ...core.dependencies import DBSession
from ...services import customer_segmentation_service

segmentation_router = APIRouter(prefix="/segmentation", tags=["Customer Segmentation"])


@segmentation_router.get("/summary")
async def get_segment_summary(db: DBSession):
    return await customer_segmentation_service.get_segment_summary(db)


@segmentation_router.post("/refresh")
async def refresh_segments(db: DBSession):
    counts = await customer_segmentation_service.auto_segment_customers(db)
    return {"message": "Segmentation updated", "counts": counts}


@segmentation_router.get("/{segment}")
async def get_customers_by_segment(
    segment: str,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await customer_segmentation_service.get_customers_by_segment(
        db, segment, page, page_size
    )
