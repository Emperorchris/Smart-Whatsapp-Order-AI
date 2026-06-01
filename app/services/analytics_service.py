import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select, distinct, case
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import exceptions, utils
from ..db.model.order_model import Order
from ..db.model.order_item_model import OrderItem
from ..db.model.customer_model import Customer
from ..db.model.carts_model import Cart
from ..db.model.conversation_model import Conversation
from ..db.model.product_model import Product
from ..db.model.inventory_model import Inventory
from ..db.model.payment_model import Payment
from ..db.model.human_hand_off_model import HumanHandOff
from ..db.model.staff_model import Staff
from ..db.schemas import analytics_schema


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


def _today_start() -> datetime:
    return _utc_now().replace(hour=0, minute=0, second=0, microsecond=0)


def _month_start() -> datetime:
    return _today_start().replace(day=1)


# ── Revenue by Period ───────────────────────────────────────────

async def get_revenue_by_period(
    db: AsyncSession,
    period: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> analytics_schema.RevenueByPeriodResponse:
    trunc = func.date_trunc(period, Order.created_at)

    query = (
        select(
            trunc.label("period"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.count(Order.id).label("order_count"),
        )
        .where(Order.status != utils.OrderStatus.CANCELLED.value)
        .group_by(trunc)
        .order_by(trunc)
    )

    if start_date:
        query = query.where(Order.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.where(Order.created_at <= datetime.combine(end_date, datetime.max.time()))

    result = await db.execute(query)
    rows = result.all()

    items = [
        analytics_schema.RevenueByPeriodItem(
            period=str(r.period),
            revenue=r.revenue,
            order_count=r.order_count,
        )
        for r in rows
    ]

    return analytics_schema.RevenueByPeriodResponse(
        items=items,
        total_revenue=sum(i.revenue for i in items) if items else Decimal(0),
        total_orders=sum(i.order_count for i in items),
    )


# ── Top Products ────────────────────────────────────────────────

async def get_top_products(
    db: AsyncSession,
    limit: int = 10,
    start_date: date | None = None,
    end_date: date | None = None,
) -> analytics_schema.TopProductsResponse:
    query = (
        select(
            OrderItem.product_id,
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.subtotal).label("total_revenue"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.status != utils.OrderStatus.CANCELLED.value)
        .group_by(OrderItem.product_id, OrderItem.product_name)
        .order_by(func.sum(OrderItem.subtotal).desc())
        .limit(limit)
    )

    if start_date:
        query = query.where(Order.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.where(Order.created_at <= datetime.combine(end_date, datetime.max.time()))

    result = await db.execute(query)

    return analytics_schema.TopProductsResponse(
        items=[
            analytics_schema.TopProductItem(
                product_id=r.product_id,
                product_name=r.product_name,
                total_quantity=r.total_quantity,
                total_revenue=r.total_revenue,
            )
            for r in result.all()
        ]
    )


# ── Top Customers ───────────────────────────────────────────────

async def get_top_customers(
    db: AsyncSession,
    limit: int = 10,
    start_date: date | None = None,
    end_date: date | None = None,
) -> analytics_schema.TopCustomersResponse:
    query = (
        select(
            Customer.id.label("customer_id"),
            Customer.name.label("customer_name"),
            Customer.whatsapp_number,
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_spent"),
        )
        .join(Order, Order.customer_id == Customer.id)
        .where(Order.status != utils.OrderStatus.CANCELLED.value)
        .group_by(Customer.id, Customer.name, Customer.whatsapp_number)
        .order_by(func.sum(Order.total_amount).desc())
        .limit(limit)
    )

    if start_date:
        query = query.where(Order.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.where(Order.created_at <= datetime.combine(end_date, datetime.max.time()))

    result = await db.execute(query)

    return analytics_schema.TopCustomersResponse(
        items=[
            analytics_schema.TopCustomerItem(
                customer_id=r.customer_id,
                customer_name=r.customer_name,
                whatsapp_number=r.whatsapp_number,
                total_orders=r.total_orders,
                total_spent=r.total_spent,
            )
            for r in result.all()
        ]
    )


# ── Conversion Rate ─────────────────────────────────────────────

async def get_conversion_rate(
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
) -> analytics_schema.ConversionRateResponse:
    cart_q = select(func.count(distinct(Cart.id)))
    order_q = select(func.count(distinct(Order.id))).where(
        Order.status != utils.OrderStatus.CANCELLED.value
    )

    if start_date:
        dt = datetime.combine(start_date, datetime.min.time())
        cart_q = cart_q.where(Cart.created_at >= dt)
        order_q = order_q.where(Order.created_at >= dt)
    if end_date:
        dt = datetime.combine(end_date, datetime.max.time())
        cart_q = cart_q.where(Cart.created_at <= dt)
        order_q = order_q.where(Order.created_at <= dt)

    total_carts = (await db.execute(cart_q)).scalar() or 0
    total_orders = (await db.execute(order_q)).scalar() or 0

    rate = (total_orders / total_carts * 100) if total_carts > 0 else 0.0

    return analytics_schema.ConversionRateResponse(
        total_carts=total_carts,
        total_orders=total_orders,
        conversion_rate=round(rate, 2),
        period_start=start_date,
        period_end=end_date,
    )


# ── Dashboard KPIs ──────────────────────────────────────────────

async def get_dashboard_kpis(db: AsyncSession) -> analytics_schema.DashboardKPIResponse:
    today = _today_start()
    month = _month_start()

    orders_today = (await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= today)
    )).scalar() or 0

    pending_orders = (await db.execute(
        select(func.count(Order.id)).where(Order.status == utils.OrderStatus.PENDING.value)
    )).scalar() or 0

    revenue_today = (await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0))
        .where(Order.created_at >= today, Order.status != utils.OrderStatus.CANCELLED.value)
    )).scalar() or Decimal(0)

    revenue_this_month = (await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0))
        .where(Order.created_at >= month, Order.status != utils.OrderStatus.CANCELLED.value)
    )).scalar() or Decimal(0)

    active_handoffs = (await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.handoff_status == utils.HandOffStatus.ACTIVE.value)
    )).scalar() or 0

    new_customers_today = (await db.execute(
        select(func.count(Customer.id)).where(Customer.created_at >= today)
    )).scalar() or 0

    new_customers_this_month = (await db.execute(
        select(func.count(Customer.id)).where(Customer.created_at >= month)
    )).scalar() or 0

    total_customers = (await db.execute(
        select(func.count(Customer.id))
    )).scalar() or 0

    total_products = (await db.execute(
        select(func.count(Product.id)).where(Product.is_active == True)
    )).scalar() or 0

    return analytics_schema.DashboardKPIResponse(
        orders_today=orders_today,
        pending_orders=pending_orders,
        revenue_today=revenue_today,
        revenue_this_month=revenue_this_month,
        active_handoffs=active_handoffs,
        new_customers_today=new_customers_today,
        new_customers_this_month=new_customers_this_month,
        total_customers=total_customers,
        total_products=total_products,
    )


# ── Order Export ────────────────────────────────────────────────

async def get_orders_for_export(
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    status: str | None = None,
) -> list[Order]:
    query = select(Order).order_by(Order.created_at.desc())

    if start_date:
        query = query.where(Order.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.where(Order.created_at <= datetime.combine(end_date, datetime.max.time()))
    if status:
        query = query.where(Order.status == status)

    result = await db.execute(query)
    return list(result.scalars().all())


def generate_orders_csv(orders: list[Order]) -> io.StringIO:
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow([
        "Order Number", "Customer Name", "WhatsApp", "Status",
        "Payment Status", "Total Amount", "Items",
        "Address", "Created At",
    ])

    for o in orders:
        items_count = len(o.order_items) if o.order_items else 0
        address = ", ".join(filter(None, [o.address_line, o.address_city, o.address_state]))
        writer.writerow([
            o.order_number,
            o.customer_name or "",
            o.customer_whatsapp_number or "",
            o.status,
            o.payment_status,
            str(o.total_amount),
            items_count,
            address,
            o.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    buffer.seek(0)
    return buffer


# ── Inventory Alerts ────────────────────────────────────────────

async def get_low_stock_items(db: AsyncSession) -> analytics_schema.LowStockResponse:
    query = (
        select(
            Inventory.id.label("inventory_id"),
            Inventory.product_id,
            Product.name.label("product_name"),
            Inventory.quantity_available,
            Inventory.low_stock_threshold,
        )
        .join(Product, Inventory.product_id == Product.id)
        .where(Inventory.quantity_available <= Inventory.low_stock_threshold)
        .order_by(Inventory.quantity_available.asc())
    )

    rows = (await db.execute(query)).all()

    items = [
        analytics_schema.LowStockItem(
            inventory_id=r.inventory_id,
            product_id=r.product_id,
            product_name=r.product_name,
            quantity_available=r.quantity_available,
            low_stock_threshold=r.low_stock_threshold,
        )
        for r in rows
    ]

    return analytics_schema.LowStockResponse(
        items=items,
        total_low_stock=len(items),
        total_out_of_stock=sum(1 for i in items if i.quantity_available == 0),
    )


# ── Payment Reconciliation ──────────────────────────────────────

async def get_payment_reconciliation(
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
) -> analytics_schema.PaymentReconciliationResponse:
    base_filter = [Order.status != utils.OrderStatus.CANCELLED.value]
    if start_date:
        base_filter.append(Order.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        base_filter.append(Order.created_at <= datetime.combine(end_date, datetime.max.time()))

    # Unpaid orders
    unpaid_q = (
        select(Order)
        .where(
            Order.payment_status == utils.PaymentStatus.PENDING.value,
            *base_filter,
        )
        .order_by(Order.created_at.desc())
    )
    unpaid_orders = list((await db.execute(unpaid_q)).scalars().all())

    unpaid_items = [
        analytics_schema.UnpaidOrderItem(
            order_id=o.id,
            order_number=o.order_number,
            customer_name=o.customer_name,
            total_amount=o.total_amount,
            status=o.status,
            payment_status=o.payment_status,
            created_at=o.created_at,
        )
        for o in unpaid_orders
    ]

    total_unpaid_amount = sum(o.total_amount for o in unpaid_orders) if unpaid_orders else Decimal(0)

    # Paid totals
    paid_q = (
        select(
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total"),
        )
        .where(
            Order.payment_status == utils.PaymentStatus.COMPLETED.value,
            *base_filter,
        )
    )
    paid_row = (await db.execute(paid_q)).one()

    return analytics_schema.PaymentReconciliationResponse(
        unpaid_orders=unpaid_items,
        total_unpaid=len(unpaid_items),
        total_unpaid_amount=total_unpaid_amount,
        total_paid=paid_row.cnt,
        total_paid_amount=paid_row.total,
    )


# ── Staff Performance ──────────────────────────────────────────

async def get_staff_performance(
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
) -> analytics_schema.StaffPerformanceResponse:
    filters = []
    if start_date:
        filters.append(HumanHandOff.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        filters.append(HumanHandOff.created_at <= datetime.combine(end_date, datetime.max.time()))

    # Total handoffs per staff
    query = (
        select(
            Staff.id.label("staff_id"),
            Staff.name.label("staff_name"),
            func.count(HumanHandOff.id).label("total_handoffs"),
            func.count(
                case(
                    (HumanHandOff.status == utils.HandOffStatus.RESOLVED.value, HumanHandOff.id),
                )
            ).label("resolved_handoffs"),
            func.avg(
                case(
                    (
                        HumanHandOff.resolved_at.isnot(None),
                        func.extract("epoch", HumanHandOff.resolved_at - HumanHandOff.claimed_at) / 60,
                    ),
                )
            ).label("avg_resolution_minutes"),
        )
        .join(HumanHandOff, HumanHandOff.assigned_staff_id == Staff.id)
        .where(*filters)
        .group_by(Staff.id, Staff.name)
        .order_by(func.count(HumanHandOff.id).desc())
    )

    rows = (await db.execute(query)).all()

    return analytics_schema.StaffPerformanceResponse(
        items=[
            analytics_schema.StaffPerformanceItem(
                staff_id=r.staff_id,
                staff_name=r.staff_name,
                total_handoffs=r.total_handoffs,
                resolved_handoffs=r.resolved_handoffs,
                avg_resolution_minutes=round(r.avg_resolution_minutes, 1) if r.avg_resolution_minutes else None,
            )
            for r in rows
        ]
    )


# ── Customer Search by Spend ───────────────────────────────────

async def get_customers_by_spend(
    db: AsyncSession,
    min_spent: Decimal | None = None,
    min_orders: int | None = None,
    segment: str | None = None,
    sort_by: str = "total_spent",
    page: int = 1,
    page_size: int = 20,
) -> analytics_schema.PaginatedCustomerSpendResponse:
    base = (
        select(
            Customer.id.label("customer_id"),
            Customer.name,
            Customer.whatsapp_number,
            Customer.customer_segment.label("segment"),
            Customer.created_at,
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_spent"),
        )
        .outerjoin(Order, (Order.customer_id == Customer.id) & (Order.status != utils.OrderStatus.CANCELLED.value))
        .group_by(Customer.id, Customer.name, Customer.whatsapp_number, Customer.customer_segment, Customer.created_at)
    )

    if segment:
        base = base.where(Customer.customer_segment == segment)

    if min_spent is not None:
        base = base.having(func.coalesce(func.sum(Order.total_amount), 0) >= min_spent)
    if min_orders is not None:
        base = base.having(func.count(Order.id) >= min_orders)

    # Count via subquery
    count_sub = base.subquery()
    total = (await db.execute(select(func.count()).select_from(count_sub))).scalar() or 0

    # Sort
    if sort_by == "total_orders":
        base = base.order_by(func.count(Order.id).desc())
    else:
        base = base.order_by(func.coalesce(func.sum(Order.total_amount), 0).desc())

    rows = (await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).all()

    return analytics_schema.PaginatedCustomerSpendResponse(
        items=[
            analytics_schema.CustomerSpendItem(
                customer_id=r.customer_id,
                name=r.name,
                whatsapp_number=r.whatsapp_number,
                total_orders=r.total_orders,
                total_spent=r.total_spent,
                segment=r.segment,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Product Export ──────────────────────────────────────────────

async def get_products_for_export(db: AsyncSession) -> list[Product]:
    result = await db.execute(select(Product).order_by(Product.created_at.desc()))
    return list(result.scalars().all())


def generate_products_csv(products: list[Product]) -> io.StringIO:
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow([
        "Name", "SKU", "Price", "Tags", "Active", "Created At",
    ])

    for p in products:
        tags = ", ".join(p.tags) if p.tags else ""
        writer.writerow([
            p.name,
            p.sku or "",
            str(p.price),
            tags,
            str(p.is_active),
            p.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    buffer.seek(0)
    return buffer


def parse_products_csv(file_content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(file_content))
    products = []
    for row in reader:
        tags_raw = row.get("Tags", "").strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None
        products.append({
            "name": row["Name"],
            "sku": row.get("SKU") or None,
            "price": Decimal(row["Price"]),
            "tags": tags,
            "is_active": row.get("Active", "True").lower() == "true",
        })
    return products


# ── Refund ──────────────────────────────────────────────────────

async def process_refund(
    db: AsyncSession,
    refund: analytics_schema.RefundRequest,
) -> analytics_schema.RefundResponse:
    result = await db.execute(select(Order).where(Order.id == refund.order_id))
    order = result.scalars().first()

    if not order:
        raise exceptions.NotFoundException("Order not found.")

    if order.status == utils.OrderStatus.CANCELLED.value:
        raise exceptions.BadRequestException("Order is already cancelled.")

    if refund.amount > order.total_amount:
        raise exceptions.BadRequestException("Refund amount exceeds order total.")

    is_full_refund = refund.amount == order.total_amount

    if is_full_refund:
        order.status = utils.OrderStatus.CANCELLED.value
        order.payment_status = utils.PaymentStatus.FULL_REFUND.value
    else:
        order.total_amount -= refund.amount

    # Record refund as a payment with negative amount
    refund_payment = Payment(
        order_id=order.id,
        payment_reference=f"REFUND-{order.order_number}-{_utc_now().strftime('%Y%m%d%H%M%S')}",
        amount=-refund.amount,
        status=utils.PaymentStatus.PARTIAL_REFUND.value if not is_full_refund else utils.PaymentStatus.FULL_REFUND.value,
        paid_at=_utc_now(),
    )
    db.add(refund_payment)

    # Store refund reason in order metadata
    meta = order.extra_metadata or {}
    refunds = meta.get("refunds", [])
    refunds.append({
        "amount": str(refund.amount),
        "reason": refund.reason,
        "at": _utc_now().isoformat(),
    })
    meta["refunds"] = refunds
    order.extra_metadata = meta

    await db.commit()
    await db.refresh(order)

    return analytics_schema.RefundResponse(
        order_id=order.id,
        order_number=order.order_number,
        refund_amount=refund.amount,
        new_order_status=order.status,
        new_payment_status=order.payment_status,
        reason=refund.reason,
    )
