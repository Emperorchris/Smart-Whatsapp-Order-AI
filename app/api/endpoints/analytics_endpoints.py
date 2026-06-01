from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Query, UploadFile, File
from fastapi.responses import StreamingResponse

from ...core.dependencies import DBSession
from ...services import analytics_service, auth_service, product_service
from ...db.schemas import analytics_schema, product_schema

analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.get("/dashboard", response_model=analytics_schema.DashboardKPIResponse)
async def get_dashboard_kpis(
    db: DBSession,
    # _: auth_service.CurrentStaff,
):
    return await analytics_service.get_dashboard_kpis(db)


@analytics_router.get("/revenue", response_model=analytics_schema.RevenueByPeriodResponse)
async def get_revenue(
    db: DBSession,
    # _: auth_service.AdminOnly,
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    return await analytics_service.get_revenue_by_period(db, period, start_date, end_date)


@analytics_router.get("/top-products", response_model=analytics_schema.TopProductsResponse)
async def get_top_products(
    db: DBSession,
    # _: auth_service.AdminOnly,
    limit: int = Query(10, ge=1, le=50),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    return await analytics_service.get_top_products(db, limit, start_date, end_date)


@analytics_router.get("/top-customers", response_model=analytics_schema.TopCustomersResponse)
async def get_top_customers(
    db: DBSession,
    # _: auth_service.AdminOnly,
    limit: int = Query(10, ge=1, le=50),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    return await analytics_service.get_top_customers(db, limit, start_date, end_date)


@analytics_router.get("/conversion-rate", response_model=analytics_schema.ConversionRateResponse)
async def get_conversion_rate(
    db: DBSession,
    # _: auth_service.AdminOnly,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    return await analytics_service.get_conversion_rate(db, start_date, end_date)


@analytics_router.get("/orders/export")
async def export_orders(
    db: DBSession,
    # _: auth_service.AdminOnly,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
):
    orders = await analytics_service.get_orders_for_export(db, start_date, end_date, status)
    buffer = analytics_service.generate_orders_csv(orders)

    filename = f"orders_export_{date.today().isoformat()}.csv"
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Inventory Alerts ────────────────────────────────────────────

@analytics_router.get("/inventory/low-stock", response_model=analytics_schema.LowStockResponse)
async def get_low_stock(db: DBSession):
    return await analytics_service.get_low_stock_items(db)


# ── Payment Reconciliation ──────────────────────────────────────

@analytics_router.get("/payments/reconciliation", response_model=analytics_schema.PaymentReconciliationResponse)
async def get_payment_reconciliation(
    db: DBSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    return await analytics_service.get_payment_reconciliation(db, start_date, end_date)


# ── Staff Performance ──────────────────────────────────────────

@analytics_router.get("/staff/performance", response_model=analytics_schema.StaffPerformanceResponse)
async def get_staff_performance(
    db: DBSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    return await analytics_service.get_staff_performance(db, start_date, end_date)


# ── Customer Search by Spend ───────────────────────────────────

@analytics_router.get("/customers/by-spend", response_model=analytics_schema.PaginatedCustomerSpendResponse)
async def get_customers_by_spend(
    db: DBSession,
    min_spent: Optional[Decimal] = None,
    min_orders: Optional[int] = None,
    segment: Optional[str] = None,
    sort_by: str = Query("total_spent", pattern="^(total_spent|total_orders)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await analytics_service.get_customers_by_spend(
        db, min_spent, min_orders, segment, sort_by, page, page_size
    )


# ── Product Export ──────────────────────────────────────────────

@analytics_router.get("/products/export")
async def export_products(db: DBSession):
    products = await analytics_service.get_products_for_export(db)
    buffer = analytics_service.generate_products_csv(products)

    filename = f"products_export_{date.today().isoformat()}.csv"
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@analytics_router.post("/products/import")
async def import_products(db: DBSession, file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8")
    rows = analytics_service.parse_products_csv(content)

    created = []
    for row in rows:
        product_data = product_schema.ProductSchema(**row)
        product = await product_service.create_product(db, product_data)
        created.append(product)

    return {"imported": len(created), "products": created}


# ── Refund ──────────────────────────────────────────────────────

@analytics_router.post("/refund", response_model=analytics_schema.RefundResponse)
async def process_refund(
    db: DBSession,
    refund: analytics_schema.RefundRequest,
):
    return await analytics_service.process_refund(db, refund)
