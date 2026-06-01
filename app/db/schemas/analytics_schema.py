from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


# ── Revenue ─────────────────────────────────────────────────────
class RevenueByPeriodItem(BaseModel):
    period: str
    revenue: Decimal
    order_count: int


class RevenueByPeriodResponse(BaseModel):
    items: list[RevenueByPeriodItem]
    total_revenue: Decimal
    total_orders: int


# ── Top Products ────────────────────────────────────────────────
class TopProductItem(BaseModel):
    product_id: UUID
    product_name: str
    total_quantity: int
    total_revenue: Decimal


class TopProductsResponse(BaseModel):
    items: list[TopProductItem]


# ── Top Customers ───────────────────────────────────────────────
class TopCustomerItem(BaseModel):
    customer_id: UUID
    customer_name: Optional[str] = None
    whatsapp_number: str
    total_orders: int
    total_spent: Decimal


class TopCustomersResponse(BaseModel):
    items: list[TopCustomerItem]


# ── Conversion Rate ─────────────────────────────────────────────
class ConversionRateResponse(BaseModel):
    total_carts: int
    total_orders: int
    conversion_rate: float
    period_start: Optional[date] = None
    period_end: Optional[date] = None


# ── Dashboard KPIs ──────────────────────────────────────────────
class DashboardKPIResponse(BaseModel):
    orders_today: int
    pending_orders: int
    revenue_today: Decimal
    revenue_this_month: Decimal
    active_handoffs: int
    new_customers_today: int
    new_customers_this_month: int
    total_customers: int
    total_products: int


# ── Inventory Alerts ────────────────────────────────────────────
class LowStockItem(BaseModel):
    inventory_id: UUID
    product_id: UUID
    product_name: str
    quantity_available: int
    low_stock_threshold: int

    model_config = {"from_attributes": True}


class LowStockResponse(BaseModel):
    items: list[LowStockItem]
    total_low_stock: int
    total_out_of_stock: int


# ── Payment Reconciliation ──────────────────────────────────────
class UnpaidOrderItem(BaseModel):
    order_id: UUID
    order_number: str
    customer_name: Optional[str] = None
    total_amount: Decimal
    status: str
    payment_status: str
    created_at: datetime


class PaymentReconciliationResponse(BaseModel):
    unpaid_orders: list[UnpaidOrderItem]
    total_unpaid: int
    total_unpaid_amount: Decimal
    total_paid: int
    total_paid_amount: Decimal


# ── Staff Performance ──────────────────────────────────────────
class StaffPerformanceItem(BaseModel):
    staff_id: UUID
    staff_name: str
    total_handoffs: int
    resolved_handoffs: int
    avg_resolution_minutes: Optional[float] = None


class StaffPerformanceResponse(BaseModel):
    items: list[StaffPerformanceItem]


# ── Customer by Spend ──────────────────────────────────────────
class CustomerSpendItem(BaseModel):
    customer_id: UUID
    name: Optional[str] = None
    whatsapp_number: str
    total_orders: int
    total_spent: Decimal
    segment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedCustomerSpendResponse(BaseModel):
    items: list[CustomerSpendItem]
    total: int
    page: int
    page_size: int


# ── Refund ──────────────────────────────────────────────────────
class RefundRequest(BaseModel):
    order_id: UUID
    amount: Decimal
    reason: str


class RefundResponse(BaseModel):
    order_id: UUID
    order_number: str
    refund_amount: Decimal
    new_order_status: str
    new_payment_status: str
    reason: str
