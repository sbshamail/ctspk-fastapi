# src/api/routers/reportRoute.py
import csv
import io
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, desc, cast, Integer, text
from sqlmodel import select

from src.api.core.response import api_response
from src.api.core.dependencies import GetSession, requirePermission
from src.api.models.order_model.orderModel import Order, OrderProduct, OrderStatus
from src.api.models.product_model.productsModel import Product
from src.api.models.category_model.categoryModel import Category
from src.api.models.shop_model.shopsModel import Shop
from src.api.models.usersModel import User
from src.api.models.withdrawModel import ShopEarning

router = APIRouter(prefix="/reports", tags=["Reports"])

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_date(d: Optional[str]) -> Optional[datetime]:
    if not d:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(d, fmt)
        except ValueError:
            continue
    return None


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    if not rows:
        output = io.StringIO()
        output.write("No data available\n")
        output.seek(0)
    else:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


def _order_date_filters(start_date: Optional[str], end_date: Optional[str]):
    filters = []
    s = _parse_date(start_date)
    e = _parse_date(end_date)
    if s:
        filters.append(Order.created_at >= s)
    if e:
        filters.append(Order.created_at <= e)
    return filters


# ─── 1. Dashboard KPIs ────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard_kpis(
    session: GetSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=requirePermission(["report:view"]),
):
    """Total revenue, orders, customers, products — summary KPIs."""
    date_filters = _order_date_filters(start_date, end_date)

    # Revenue: sum paid_total on completed orders
    rev_q = select(func.coalesce(func.sum(Order.paid_total), 0)).where(
        Order.order_status == "order-completed", *date_filters
    )
    total_revenue = session.execute(rev_q).scalar()

    # All orders (regardless of status)
    ord_q = select(func.count(Order.id)).where(*date_filters)
    total_orders = session.execute(ord_q).scalar()

    # Unique customers who placed orders
    cust_q = select(func.count(func.distinct(Order.customer_id))).where(*date_filters)
    total_customers = session.execute(cust_q).scalar()

    # Active products
    prod_q = select(func.count(Product.id)).where(
        Product.deleted_at == None, Product.is_active == True  # noqa: E711
    )
    total_products = session.execute(prod_q).scalar()

    # Pending orders
    pend_q = select(func.count(Order.id)).where(
        Order.order_status == "order-pending", *date_filters
    )
    pending_orders = session.execute(pend_q).scalar()

    # Average order value
    avg_q = select(func.coalesce(func.avg(Order.paid_total), 0)).where(
        Order.order_status == "order-completed", *date_filters
    )
    avg_order_value = float(session.execute(avg_q).scalar())

    return api_response(200, "Dashboard KPIs", {
        "total_revenue": f"{float(total_revenue):.2f}",
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "total_customers": total_customers,
        "total_products": total_products,
        "avg_order_value": f"{avg_order_value:.2f}",
    })


# ─── 2. Sales Trend ───────────────────────────────────────────────────────────

@router.get("/sales-trend")
def sales_trend(
    session: GetSession,
    period: str = Query("day", regex="^(day|week|month)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=requirePermission(["report:view"]),
):
    """Daily / weekly / monthly revenue and order count trend."""
    date_filters = _order_date_filters(start_date, end_date)

    # Default look-back if no dates given
    if not start_date and not end_date:
        lookback = {"day": 30, "week": 84, "month": 365}[period]
        date_filters = [Order.created_at >= datetime.utcnow() - timedelta(days=lookback)]

    period_label = func.date_trunc(period, Order.created_at).label("period")

    rows = session.execute(
        select(
            period_label,
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.paid_total), 0).label("revenue"),
        )
        .where(*date_filters)
        .group_by(period_label)
        .order_by(period_label)
    ).all()

    data = [
        {
            "period": str(r.period)[:10] if r.period else None,
            "orders": r.orders,
            "revenue": f"{float(r.revenue):.2f}",
        }
        for r in rows
    ]
    return api_response(200, "Sales trend", data, len(data))


# ─── 3. Top-Selling Products ──────────────────────────────────────────────────

@router.get("/top-products")
def top_products(
    session: GetSession,
    limit: int = Query(10, ge=1, le=100),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=requirePermission(["report:view"]),
):
    """Top products by units sold and revenue."""
    date_filters = []
    s = _parse_date(start_date)
    e = _parse_date(end_date)
    if s:
        date_filters.append(Order.created_at >= s)
    if e:
        date_filters.append(Order.created_at <= e)

    q = (
        select(
            Product.id,
            Product.name,
            Product.sku,
            func.sum(cast(OrderProduct.order_quantity, Integer)).label("units_sold"),
            func.sum(OrderProduct.subtotal).label("revenue"),
            func.count(func.distinct(OrderProduct.order_id)).label("order_count"),
        )
        .join(OrderProduct, OrderProduct.product_id == Product.id)
        .join(Order, Order.id == OrderProduct.order_id)
        .where(*date_filters)
        .group_by(Product.id, Product.name, Product.sku)
        .order_by(desc("units_sold"))
        .limit(limit)
    )

    rows = session.execute(q).all()
    data = [
        {
            "product_id": r.id,
            "name": r.name,
            "sku": r.sku,
            "units_sold": int(r.units_sold or 0),
            "revenue": f"{float(r.revenue or 0):.2f}",
            "order_count": r.order_count,
        }
        for r in rows
    ]
    return api_response(200, "Top products", data, len(data))


# ─── 4. Top-Selling Categories ────────────────────────────────────────────────

@router.get("/top-categories")
def top_categories(
    session: GetSession,
    limit: int = Query(10, ge=1, le=50),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=requirePermission(["report:view"]),
):
    """Top categories by revenue and units sold."""
    date_filters = []
    s = _parse_date(start_date)
    e = _parse_date(end_date)
    if s:
        date_filters.append(Order.created_at >= s)
    if e:
        date_filters.append(Order.created_at <= e)

    q = (
        select(
            Category.id,
            Category.name,
            func.sum(cast(OrderProduct.order_quantity, Integer)).label("units_sold"),
            func.sum(OrderProduct.subtotal).label("revenue"),
            func.count(func.distinct(OrderProduct.order_id)).label("order_count"),
        )
        .join(Product, Product.category_id == Category.id)
        .join(OrderProduct, OrderProduct.product_id == Product.id)
        .join(Order, Order.id == OrderProduct.order_id)
        .where(*date_filters)
        .group_by(Category.id, Category.name)
        .order_by(desc("revenue"))
        .limit(limit)
    )

    rows = session.execute(q).all()
    data = [
        {
            "category_id": r.id,
            "name": r.name,
            "units_sold": int(r.units_sold or 0),
            "revenue": f"{float(r.revenue or 0):.2f}",
            "order_count": r.order_count,
        }
        for r in rows
    ]
    return api_response(200, "Top categories", data, len(data))


# ─── 5. Vendor Earnings Report ────────────────────────────────────────────────

@router.get("/vendor-earnings")
def vendor_earnings(
    session: GetSession,
    shop_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = Query(20, ge=1, le=100),
    user=requirePermission(["report:view"]),
):
    """Per-vendor earnings: revenue, admin commission, net earnings."""
    date_filters = []
    s = _parse_date(start_date)
    e = _parse_date(end_date)
    if s:
        date_filters.append(ShopEarning.created_at >= s)
    if e:
        date_filters.append(ShopEarning.created_at <= e)
    if shop_id:
        date_filters.append(ShopEarning.shop_id == shop_id)

    q = (
        select(
            Shop.id,
            Shop.name,
            func.count(func.distinct(ShopEarning.order_id)).label("total_orders"),
            func.sum(ShopEarning.order_amount).label("gross_revenue"),
            func.sum(ShopEarning.admin_commission).label("admin_commission"),
            func.sum(ShopEarning.shop_earning).label("net_earnings"),
            func.sum(ShopEarning.settled_amount).label("settled_amount"),
        )
        .join(ShopEarning, ShopEarning.shop_id == Shop.id)
        .where(*date_filters)
        .group_by(Shop.id, Shop.name)
        .order_by(desc("gross_revenue"))
    )

    total = session.execute(select(func.count()).select_from(q.subquery())).scalar()
    offset = (page - 1) * limit
    rows = session.execute(q.offset(offset).limit(limit)).all()

    data = [
        {
            "shop_id": r.id,
            "shop_name": r.name,
            "total_orders": r.total_orders,
            "gross_revenue": f"{float(r.gross_revenue or 0):.2f}",
            "admin_commission": f"{float(r.admin_commission or 0):.2f}",
            "net_earnings": f"{float(r.net_earnings or 0):.2f}",
            "settled_amount": f"{float(r.settled_amount or 0):.2f}",
        }
        for r in rows
    ]
    return api_response(200, "Vendor earnings", data, total)


# ─── 6. Inventory Health ──────────────────────────────────────────────────────

@router.get("/inventory-health")
def inventory_health(
    session: GetSession,
    low_stock_threshold: int = Query(10, ge=0),
    slow_mover_days: int = Query(30, ge=7),
    page: int = 1,
    limit: int = Query(20, ge=1, le=100),
    user=requirePermission(["report:view"]),
):
    """Stock levels, low-stock items, out-of-stock, and slow movers."""
    # Summary counts
    total_active = session.execute(
        select(func.count(Product.id)).where(Product.deleted_at == None, Product.is_active == True)  # noqa: E711
    ).scalar()

    out_of_stock = session.execute(
        select(func.count(Product.id)).where(
            Product.deleted_at == None, Product.quantity == 0  # noqa: E711
        )
    ).scalar()

    low_stock = session.execute(
        select(func.count(Product.id)).where(
            Product.deleted_at == None,  # noqa: E711
            Product.quantity > 0,
            Product.quantity <= low_stock_threshold,
        )
    ).scalar()

    # Slow movers: products with no orders in the past N days
    cutoff = datetime.utcnow() - timedelta(days=slow_mover_days)
    sold_ids_q = select(func.distinct(OrderProduct.product_id)).join(
        Order, Order.id == OrderProduct.order_id
    ).where(Order.created_at >= cutoff)

    offset = (page - 1) * limit
    slow_movers_q = (
        select(Product.id, Product.name, Product.sku, Product.quantity, Product.price)
        .where(
            Product.deleted_at == None,  # noqa: E711
            Product.is_active == True,
            Product.quantity > 0,
            ~Product.id.in_(sold_ids_q),
        )
        .order_by(Product.quantity)
        .offset(offset)
        .limit(limit)
    )

    slow_mover_rows = session.execute(slow_movers_q).all()
    slow_mover_total = session.execute(
        select(func.count()).select_from(slow_movers_q.subquery())
    ).scalar()

    slow_movers = [
        {
            "product_id": r.id,
            "name": r.name,
            "sku": r.sku,
            "quantity": r.quantity,
            "price": f"{float(r.price or 0):.2f}",
        }
        for r in slow_mover_rows
    ]

    return api_response(200, "Inventory health", {
        "summary": {
            "total_active_products": total_active,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "low_stock_threshold": low_stock_threshold,
        },
        "slow_movers": slow_movers,
        "slow_mover_total": slow_mover_total,
        "slow_mover_days": slow_mover_days,
    })


# ─── 7. Order Fulfillment Time Analytics ─────────────────────────────────────

@router.get("/fulfillment-time")
def fulfillment_time(
    session: GetSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=requirePermission(["report:view"]),
):
    """Average time (hours) from order placed to completed/delivered."""
    date_filters = []
    s = _parse_date(start_date)
    e = _parse_date(end_date)
    if s:
        date_filters.append(OrderStatus.created_at >= s)
    if e:
        date_filters.append(OrderStatus.created_at <= e)

    rows = session.execute(
        select(
            OrderStatus.order_pending_date,
            OrderStatus.order_processing_date,
            OrderStatus.order_packed_date,
            OrderStatus.order_at_local_facility_date,
            OrderStatus.order_out_for_delivery_date,
            OrderStatus.order_completed_date,
            OrderStatus.order_deliver_date,
        ).where(
            OrderStatus.order_pending_date != None,  # noqa: E711
            *date_filters,
        )
    ).all()

    def _hours(a, b) -> Optional[float]:
        if a and b:
            delta = b - a
            return round(delta.total_seconds() / 3600, 2)
        return None

    pending_to_completed = []
    pending_to_delivered = []
    pending_to_processing = []

    for r in rows:
        h1 = _hours(r.order_pending_date, r.order_completed_date)
        h2 = _hours(r.order_pending_date, r.order_deliver_date)
        h3 = _hours(r.order_pending_date, r.order_processing_date)
        if h1 is not None:
            pending_to_completed.append(h1)
        if h2 is not None:
            pending_to_delivered.append(h2)
        if h3 is not None:
            pending_to_processing.append(h3)

    def _avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else None

    return api_response(200, "Fulfillment time analytics", {
        "total_orders_analyzed": len(rows),
        "avg_hours_pending_to_processing": _avg(pending_to_processing),
        "avg_hours_pending_to_completed": _avg(pending_to_completed),
        "avg_hours_pending_to_delivered": _avg(pending_to_delivered),
    })


# ─── 8. Customer Acquisition & Retention ─────────────────────────────────────

@router.get("/customer-metrics")
def customer_metrics(
    session: GetSession,
    period: str = Query("month", regex="^(day|week|month)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=requirePermission(["report:view"]),
):
    """New customers per period, repeat buyers, avg orders per customer."""
    date_filters = _order_date_filters(start_date, end_date)
    if not start_date and not end_date:
        lookback = {"day": 30, "week": 84, "month": 365}[period]
        date_filters = [Order.created_at >= datetime.utcnow() - timedelta(days=lookback)]

    # New registrations trend
    reg_period = func.date_trunc(period, User.created_at).label("period")
    reg_rows = session.execute(
        select(reg_period, func.count(User.id).label("new_customers"))
        .where(*date_filters)
        .group_by(reg_period)
        .order_by(reg_period)
    ).all()

    # Repeat buyers: customers with more than 1 order in date range
    buyer_q = (
        select(Order.customer_id, func.count(Order.id).label("order_count"))
        .where(Order.customer_id != None, *date_filters)  # noqa: E711
        .group_by(Order.customer_id)
    ).subquery()

    repeat_buyers = session.execute(
        select(func.count()).select_from(buyer_q).where(buyer_q.c.order_count > 1)
    ).scalar()

    one_time_buyers = session.execute(
        select(func.count()).select_from(buyer_q).where(buyer_q.c.order_count == 1)
    ).scalar()

    avg_orders = session.execute(
        select(func.avg(buyer_q.c.order_count))
    ).scalar()

    # Avg order value per customer
    avg_spend = session.execute(
        select(func.coalesce(func.avg(Order.paid_total), 0)).where(
            Order.order_status == "order-completed", *date_filters
        )
    ).scalar()

    new_by_period = [
        {"period": str(r.period)[:10] if r.period else None, "new_customers": r.new_customers}
        for r in reg_rows
    ]

    return api_response(200, "Customer metrics", {
        "new_customers_trend": new_by_period,
        "repeat_buyers": repeat_buyers,
        "one_time_buyers": one_time_buyers,
        "avg_orders_per_customer": round(float(avg_orders or 0), 2),
        "avg_spend_per_order": f"{float(avg_spend or 0):.2f}",
    })


# ─── 9. CSV Exports ───────────────────────────────────────────────────────────

@router.get("/export/orders")
def export_orders_csv(
    session: GetSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    user=requirePermission(["report:view"]),
):
    """Export orders to CSV."""
    date_filters = _order_date_filters(start_date, end_date)
    if status:
        date_filters.append(Order.order_status == status)

    rows = session.execute(
        select(
            Order.id,
            Order.tracking_number,
            Order.customer_name,
            Order.customer_contact,
            Order.order_status,
            Order.payment_status,
            Order.payment_gateway,
            Order.total,
            Order.paid_total,
            Order.delivery_fee,
            Order.discount,
            Order.coupon_discount,
            Order.sales_tax,
            Order.created_at,
        )
        .where(*date_filters)
        .order_by(desc(Order.created_at))
    ).all()

    data = [
        {
            "Order ID": r.id,
            "Tracking #": r.tracking_number,
            "Customer": r.customer_name,
            "Contact": r.customer_contact,
            "Status": r.order_status,
            "Payment Status": r.payment_status,
            "Gateway": r.payment_gateway,
            "Total": f"{float(r.total or 0):.2f}",
            "Paid Total": f"{float(r.paid_total or 0):.2f}",
            "Delivery Fee": f"{float(r.delivery_fee or 0):.2f}",
            "Discount": f"{float(r.discount or 0):.2f}",
            "Coupon Discount": f"{float(r.coupon_discount or 0):.2f}",
            "Sales Tax": f"{float(r.sales_tax or 0):.2f}",
            "Date": str(r.created_at)[:19] if r.created_at else "",
        }
        for r in rows
    ]
    return _csv_response(data, "orders_export")


@router.get("/export/sales")
def export_sales_csv(
    session: GetSession,
    period: str = Query("day", regex="^(day|week|month)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=requirePermission(["report:view"]),
):
    """Export sales trend data to CSV."""
    date_filters = _order_date_filters(start_date, end_date)
    if not start_date and not end_date:
        lookback = {"day": 30, "week": 84, "month": 365}[period]
        date_filters = [Order.created_at >= datetime.utcnow() - timedelta(days=lookback)]

    period_label = func.date_trunc(period, Order.created_at).label("period")
    rows = session.execute(
        select(
            period_label,
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.paid_total), 0).label("revenue"),
        )
        .where(*date_filters)
        .group_by(period_label)
        .order_by(period_label)
    ).all()

    data = [
        {
            "Period": str(r.period)[:10] if r.period else "",
            "Orders": r.orders,
            "Revenue": f"{float(r.revenue):.2f}",
        }
        for r in rows
    ]
    return _csv_response(data, f"sales_trend_{period}")


@router.get("/export/vendor-earnings")
def export_vendor_earnings_csv(
    session: GetSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=requirePermission(["report:view"]),
):
    """Export vendor earnings to CSV."""
    date_filters = []
    s = _parse_date(start_date)
    e = _parse_date(end_date)
    if s:
        date_filters.append(ShopEarning.created_at >= s)
    if e:
        date_filters.append(ShopEarning.created_at <= e)

    rows = session.execute(
        select(
            Shop.id,
            Shop.name,
            func.count(func.distinct(ShopEarning.order_id)).label("total_orders"),
            func.sum(ShopEarning.order_amount).label("gross_revenue"),
            func.sum(ShopEarning.admin_commission).label("admin_commission"),
            func.sum(ShopEarning.shop_earning).label("net_earnings"),
            func.sum(ShopEarning.settled_amount).label("settled_amount"),
        )
        .join(ShopEarning, ShopEarning.shop_id == Shop.id)
        .where(*date_filters)
        .group_by(Shop.id, Shop.name)
        .order_by(desc("gross_revenue"))
    ).all()

    data = [
        {
            "Shop ID": r.id,
            "Shop Name": r.name,
            "Total Orders": r.total_orders,
            "Gross Revenue": f"{float(r.gross_revenue or 0):.2f}",
            "Admin Commission": f"{float(r.admin_commission or 0):.2f}",
            "Net Earnings": f"{float(r.net_earnings or 0):.2f}",
            "Settled Amount": f"{float(r.settled_amount or 0):.2f}",
        }
        for r in rows
    ]
    return _csv_response(data, "vendor_earnings")


@router.get("/export/inventory")
def export_inventory_csv(
    session: GetSession,
    low_stock_threshold: int = Query(10, ge=0),
    user=requirePermission(["report:view"]),
):
    """Export inventory health report to CSV."""
    rows = session.execute(
        select(
            Product.id,
            Product.name,
            Product.sku,
            Product.quantity,
            Product.price,
            Product.sale_price,
            Product.in_stock,
            Product.total_sold_quantity,
            Category.name.label("category"),
            Shop.name.label("shop"),
        )
        .join(Category, Category.id == Product.category_id, isouter=True)
        .join(Shop, Shop.id == Product.shop_id, isouter=True)
        .where(Product.deleted_at == None, Product.is_active == True)  # noqa: E711
        .order_by(Product.quantity)
    ).all()

    data = [
        {
            "Product ID": r.id,
            "Name": r.name,
            "SKU": r.sku,
            "Quantity": r.quantity,
            "Price": f"{float(r.price or 0):.2f}",
            "Sale Price": f"{float(r.sale_price or 0):.2f}",
            "In Stock": r.in_stock,
            "Total Sold": r.total_sold_quantity,
            "Stock Status": "Out of Stock" if r.quantity == 0 else ("Low Stock" if r.quantity <= low_stock_threshold else "In Stock"),
            "Category": r.category or "",
            "Shop": r.shop or "",
        }
        for r in rows
    ]
    return _csv_response(data, "inventory_report")
