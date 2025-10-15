# src/api/routes/orderRoute.py
import ast
from typing import Optional,Dict,Any
from fastapi import APIRouter, Query
from sqlalchemy import select
from src.api.core.utility import Print, uniqueSlugify
from src.api.core.operation import listop, updateOp
from src.api.core.response import api_response, raiseExceptions
from sqlalchemy.orm import selectinload, joinedload
from src.api.models.order_model.orderModel import (
    Order, OrderCreate, OrderUpdate, OrderRead, OrderReadNested, 
    OrderStatusUpdate, OrderProduct, OrderStatus, OrderStatusEnum, 
    PaymentStatusEnum, OrderItemType, OrderGroupedItem,OrderProductCreate
)
from src.api.models.product_model.productsModel import Product, ProductType, GroupedProductPricingType
from src.api.models.product_model.variationOptionModel import VariationOption
from src.api.models.category_model import Category
#from src.api.models.withdrawModel import ShopEarning
from src.api.core.dependencies import GetSession, requirePermission
from datetime import datetime
import uuid
from decimal import Decimal

router = APIRouter(prefix="/order", tags=["Order"])


def generate_tracking_number():
    """Generate unique tracking number"""
    return f"TRK-{uuid.uuid4().hex[:12].upper()}"


def get_product_snapshot(session, product_id: int) -> Dict[str, Any]:
    """Get product snapshot for order record"""
    product = session.get(Product, product_id)
    if not product:
        return {}
    
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "sku": product.sku,
        "price": product.price,
        "sale_price": product.sale_price,
        "image": product.image,
        "product_type": product.product_type,
        "purchase_price": product.purchase_price,
    }


def get_variation_snapshot(session, variation_option_id: int) -> Dict[str, Any]:
    """Get variation snapshot for order record"""
    variation = session.get(VariationOption, variation_option_id)
    if not variation:
        return {}
    
    return {
        "id": variation.id,
        "title": variation.title,
        "price": variation.price,
        "sale_price": variation.sale_price,
        "sku": variation.sku,
        "options": variation.options,
        "image": variation.image,
        "purchase_price": variation.purchase_price,
    }


def validate_product_availability(session, product_data: OrderProductCreate) -> tuple[bool, str]:
    """Validate product availability based on type"""
    product = session.get(Product, product_data.product_id)
    if not product or not product.is_active:
        return False, "Product not found or inactive"
    
    if product_data.item_type == OrderItemType.SIMPLE:
        if product.quantity >= float(product_data.order_quantity) and product.in_stock:
            return True, "Available"
        else:
            return False, f"Insufficient stock. Available: {product.quantity}, Requested: {product_data.order_quantity}"
    
    elif product_data.item_type == OrderItemType.VARIABLE:
        if not product_data.variation_option_id:
            return False, "Variation option ID required for variable product"
        variation = session.get(VariationOption, product_data.variation_option_id)
        if variation and variation.quantity >= float(product_data.order_quantity) and variation.is_active:
            return True, "Available"
        else:
            available_qty = variation.quantity if variation else 0
            return False, f"Insufficient variation stock. Available: {available_qty}, Requested: {product_data.order_quantity}"
    
    elif product_data.item_type == OrderItemType.GROUPED:
        if not product_data.grouped_items:
            return False, "Grouped items required for grouped product"
        
        # Check availability for all grouped items
        for grouped_item in product_data.grouped_items:
            grouped_product = session.get(Product, grouped_item.product_id)
            if not grouped_product:
                return False, f"Grouped product {grouped_item.product_id} not found"
            if grouped_product.quantity < grouped_item.quantity:
                return False, f"Insufficient stock for {grouped_product.name}. Available: {grouped_product.quantity}, Required: {grouped_item.quantity}"
        return True, "All grouped items available"
    
    return False, "Unknown product type"


def update_product_inventory(session, product_data: OrderProductCreate, operation: str = "deduct"):
    """Update product inventory based on product type and track sales"""
    multiplier = -1 if operation == "deduct" else 1
    
    if product_data.item_type == OrderItemType.SIMPLE:
        product = session.get(Product, product_data.product_id)
        if product:
            quantity_change = multiplier * float(product_data.order_quantity)
            product.quantity += quantity_change
            
            # Update sales tracking
            if operation == "deduct":
                product.total_sold_quantity += float(product_data.order_quantity)
            else:  # restore/refund
                product.total_sold_quantity -= float(product_data.order_quantity)
                
            if product.quantity <= 0:
                product.in_stock = False
            else:
                product.in_stock = True
            session.add(product)
    
    elif product_data.item_type == OrderItemType.VARIABLE and product_data.variation_option_id:
        variation = session.get(VariationOption, product_data.variation_option_id)
        if variation:
            quantity_change = multiplier * float(product_data.order_quantity)
            variation.quantity += quantity_change
            
            # Update parent product quantity and sales tracking
            product = session.get(Product, product_data.product_id)
            if product:
                if operation == "deduct":
                    product.total_sold_quantity += float(product_data.order_quantity)
                else:
                    product.total_sold_quantity -= float(product_data.order_quantity)
                
                # Recalculate total quantity from variations
                variations = session.exec(
                    select(VariationOption).where(VariationOption.product_id == product_data.product_id)
                ).all()
                product.quantity = sum(var.quantity for var in variations)
                session.add(product)
            
            if variation.quantity <= 0:
                variation.is_active = False
            session.add(variation)
    
    elif product_data.item_type == OrderItemType.GROUPED and product_data.grouped_items:
        for grouped_item in product_data.grouped_items:
            grouped_product = session.get(Product, grouped_item.product_id)
            if grouped_product:
                quantity_change = multiplier * grouped_item.quantity
                grouped_product.quantity += quantity_change
                
                # Update sales tracking for constituent products
                if operation == "deduct":
                    grouped_product.total_sold_quantity += grouped_item.quantity
                else:
                    grouped_product.total_sold_quantity -= grouped_item.quantity
                    
                if grouped_product.quantity <= 0:
                    grouped_product.in_stock = False
                else:
                    grouped_product.in_stock = True
                session.add(grouped_product)


def calculate_admin_commission(
    session, product_id: int, unit_price: float, order_quantity: str
) -> Decimal:
    """Calculate admin commission based on product's category commission rate"""
    try:
        product = session.exec(
            select(Product).where(Product.id == product_id)
        ).scalar_one_or_none()

        if not product or not product.category_id:
            return Decimal("0.00")

        category = session.get(Category, product.category_id)
        if not category or not category.admin_commission_rate:
            return Decimal("0.00")

        quantity = float(order_quantity)
        commission_amount = (unit_price * quantity) * (category.admin_commission_rate / 100)

        return Decimal(str(round(commission_amount, 2)))

    except (ValueError, TypeError) as e:
        Print(f"Error calculating commission: {e}")
        return Decimal("0.00")


def update_order_status_history(session, order_id: int, status_field: str):
    """Update order status history when order status changes"""
    order_status = session.exec(
        select(OrderStatus).where(OrderStatus.order_id == order_id)
    ).first()

    if not order_status:
        order_status = OrderStatus(order_id=order_id)
        session.add(order_status)

    setattr(order_status, status_field, datetime.now())
    session.add(order_status)


@router.post("/create")
def create(request: OrderCreate, session: GetSession, user=requirePermission("order")):
    # Validate all products before creating order
    validation_errors = []
    for product_data in request.order_products:
        is_available, message = validate_product_availability(session, product_data)
        if not is_available:
            validation_errors.append(f"Product {product_data.product_id}: {message}")
    
    if validation_errors:
        return api_response(400, "Product availability issues", {"errors": validation_errors})

    # Generate tracking number
    tracking_number = generate_tracking_number()

    # Create order
    order_data = request.model_dump(exclude={"order_products"})
    order = Order(**order_data, tracking_number=tracking_number)

    session.add(order)
    session.flush()

    total_admin_commission = Decimal("0.00")

    # Create order products with proper type handling
    for product_data in request.order_products:
        # Calculate admin commission
        admin_commission = calculate_admin_commission(
            session,
            product_data.product_id,
            product_data.unit_price,
            product_data.order_quantity,
        )
        total_admin_commission += admin_commission

        # Create product snapshots
        product_snapshot = get_product_snapshot(session, product_data.product_id)
        variation_snapshot = None
        if product_data.variation_option_id:
            variation_snapshot = get_variation_snapshot(session, product_data.variation_option_id)

        # Create order product
        order_product = OrderProduct(
            **product_data.model_dump(exclude={"grouped_items"}),
            order_id=order.id,
            admin_commission=admin_commission,
            product_snapshot=product_snapshot,
            variation_snapshot=variation_snapshot,
            grouped_items=product_data.grouped_items if product_data.grouped_items else None,
        )
        session.add(order_product)

        # Update inventory (deduct quantities)
        update_product_inventory(session, product_data, "deduct")

    # Update order with total admin commission
    order.admin_commission_amount = total_admin_commission

    # Create initial order status history
    order_status = OrderStatus(order_id=order.id, order_pending_date=datetime.now())
    session.add(order_status)

    session.commit()
    session.refresh(order)

    return api_response(
        201, "Order Created Successfully", OrderReadNested.model_validate(order)
    )


@router.put("/update/{id}")
def update(
    id: int,
    request: OrderUpdate,
    session: GetSession,
    user=requirePermission("order"),
):
    order = session.get(Order, id)
    raiseExceptions((order, 404, "Order not found"))

    # Track status changes for history
    old_order_status = order.order_status

    data = updateOp(order, request, session)

    # Update status history if order status changed
    if request.order_status and request.order_status != old_order_status:
        status_field_map = {
            OrderStatusEnum.PENDING: "order_pending_date",
            OrderStatusEnum.PROCESSING: "order_processing_date",
            OrderStatusEnum.COMPLETED: "order_completed_date",
            OrderStatusEnum.REFUNDED: "order_refunded_date",
            OrderStatusEnum.FAILED: "order_failed_date",
            OrderStatusEnum.CANCELLED: "order_cancelled_date",
            OrderStatusEnum.AT_LOCAL_FACILITY: "order_at_local_facility_date",
            OrderStatusEnum.OUT_FOR_DELIVERY: "order_out_for_delivery_date",
            OrderStatusEnum.AT_DISTRIBUTION_CENTER: "order_at_distribution_center_date",
            OrderStatusEnum.PACKED: "order_packed_date",
        }

        status_field = status_field_map.get(request.order_status)
        if status_field:
            update_order_status_history(session, order.id, status_field)
            
    session.commit()
    session.refresh(order)
    #create_shop_earning(session, order)
    return api_response(
        200, "Order Updated Successfully", OrderReadNested.model_validate(order)
    )


@router.patch("/{id}/status")
def update_status(
    id: int,
    request: OrderStatusUpdate,
    session: GetSession,
    user=requirePermission("order"),
):
    order = session.get(Order, id)
    raiseExceptions((order, 404, "Order not found"))

    # Handle inventory restoration for cancelled/refunded orders
    if (request.order_status in [OrderStatusEnum.CANCELLED, OrderStatusEnum.REFUNDED] and 
        order.order_status not in [OrderStatusEnum.CANCELLED, OrderStatusEnum.REFUNDED]):
        
        # Restore inventory for all order products
        order_products = session.exec(
            select(OrderProduct).where(OrderProduct.order_id == id)
        ).all()
        
        for order_product in order_products:
            product_data = OrderProductCreate(
                product_id=order_product.product_id,
                variation_option_id=order_product.variation_option_id,
                order_quantity=order_product.order_quantity,
                unit_price=order_product.unit_price,
                subtotal=order_product.subtotal,
                item_type=order_product.item_type,
                grouped_items=order_product.grouped_items,
            )
            update_product_inventory(session, product_data, "restore")

    # Update order status
    if request.order_status:
        old_status = order.order_status
        order.order_status = request.order_status

        # Update status history
        status_field_map = {
            OrderStatusEnum.PENDING: "order_pending_date",
            OrderStatusEnum.PROCESSING: "order_processing_date",
            OrderStatusEnum.COMPLETED: "order_completed_date",
            OrderStatusEnum.REFUNDED: "order_refunded_date",
            OrderStatusEnum.FAILED: "order_failed_date",
            OrderStatusEnum.CANCELLED: "order_cancelled_date",
            OrderStatusEnum.AT_LOCAL_FACILITY: "order_at_local_facility_date",
            OrderStatusEnum.OUT_FOR_DELIVERY: "order_out_for_delivery_date",
            OrderStatusEnum.AT_DISTRIBUTION_CENTER: "order_at_distribution_center_date",
            OrderStatusEnum.PACKED: "order_packed_date",
        }

        status_field = status_field_map.get(request.order_status)
        if status_field:
            update_order_status_history(session, order.id, status_field)

    # Update payment status
    if request.payment_status:
        order.payment_status = request.payment_status

    session.add(order)
    session.commit()
    session.refresh(order)
    #create_shop_earning(session, order)
    return api_response(
        200, "Order Status Updated Successfully", OrderRead.model_validate(order)
    )


@router.get("/read/{id}", response_model=OrderReadNested)
def get(id: int, session: GetSession, user=requirePermission("order")):
    order = session.get(Order, id)
    raiseExceptions((order, 404, "Order not found"))

    return api_response(200, "Order Found", OrderReadNested.model_validate(order))


@router.get("/tracking/{tracking_number}", response_model=OrderReadNested)
def get_by_tracking(tracking_number: str, session: GetSession):
    order = session.exec(
        select(Order).where(Order.tracking_number == tracking_number)
    ).first()
    raiseExceptions((order, 404, "Order not found"))

    return api_response(200, "Order Found", OrderReadNested.model_validate(order))


@router.delete("/delete/{id}")
def delete(
    id: int,
    session: GetSession,
    user=requirePermission("order-delete"),
):
    order = session.get(Order, id)
    raiseExceptions((order, 404, "Order not found"))

    # Restore inventory before deletion
    order_products = session.exec(
        select(OrderProduct).where(OrderProduct.order_id == id)
    ).all()
    
    for order_product in order_products:
        product_data = OrderProductCreate(
            product_id=order_product.product_id,
            variation_option_id=order_product.variation_option_id,
            order_quantity=order_product.order_quantity,
            unit_price=order_product.unit_price,
            subtotal=order_product.subtotal,
            item_type=order_product.item_type,
            grouped_items=order_product.grouped_items,
        )
        update_product_inventory(session, product_data, "restore")

    # Delete related order products
    for op in order_products:
        session.delete(op)

    # Delete order status history
    order_status = session.exec(
        select(OrderStatus).where(OrderStatus.order_id == id)
    ).first()
    if order_status:
        session.delete(order_status)

    # Delete order
    session.delete(order)
    session.commit()

    return api_response(200, f"Order {order.tracking_number} deleted successfully")


@router.get("/list", response_model=list[OrderReadNested])
def list_orders(
    session: GetSession,
    dateRange: Optional[str] = None,
    numberRange: Optional[str] = None,
    searchTerm: str = None,
    columnFilters: Optional[str] = Query(None),
    order_status: Optional[OrderStatusEnum] = None,
    payment_status: Optional[PaymentStatusEnum] = None,
    page: int = None,
    skip: int = 0,
    limit: int = Query(200, ge=1, le=200),
):
    filters = {
        "searchTerm": searchTerm,
        "columnFilters": columnFilters,
        "dateRange": dateRange,
        "numberRange": numberRange,
    }

    searchFields = ["tracking_number", "customer_contact", "customer_name"]

    # Add status filters
    if order_status:
        if "columnFilters" not in filters or not filters["columnFilters"]:
            filters["columnFilters"] = []
        filters["columnFilters"].append(["order_status", order_status.value])

    if payment_status:
        if "columnFilters" not in filters or not filters["columnFilters"]:
            filters["columnFilters"] = []
        filters["columnFilters"].append(["payment_status", payment_status.value])

    result = listop(
        session=session,
        Model=Order,
        searchFields=searchFields,
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
    )

    if not result["data"]:
        return api_response(404, "No orders found")

    list_data = [OrderReadNested.model_validate(prod) for prod in result["data"]]
    return api_response(200, "Orders found", list_data, result["total"])


@router.get("/customer/{customer_id}", response_model=list[OrderReadNested])
def get_customer_orders(
    customer_id: int,
    session: GetSession,
    page: int = None,
    skip: int = 0,
    limit: int = Query(200, ge=1, le=200),
):
    """Get orders for a specific customer"""
    filters = {"columnFilters": [["customer_id", str(customer_id)]]}

    result = listop(
        session=session,
        Model=Order,
        searchFields=[],
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
    )

    if not result["data"]:
        return api_response(404, "No orders found for this customer")

    orders = result["data"]
    return api_response(200, "Customer orders found", orders, result["total"])


# Product Sales Report
@router.get("/sales-report")
def get_sales_report(
    session: GetSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    shop_id: Optional[int] = None,
    product_id: Optional[int] = None,
    user=requirePermission("order"),
):
    """Get sales report with product-wise sales data"""
    try:
        # Build base query for completed orders
        query = select(Order).where(Order.order_status == OrderStatusEnum.COMPLETED)
        
        # Apply date filters
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(Order.created_at >= start_dt)
        
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.where(Order.created_at <= end_dt)
        
        if shop_id:
            query = query.where(Order.shop_id == shop_id)
        
        orders = session.exec(query).all()
        
        sales_data = {}
        total_revenue = 0
        total_products_sold = 0
        
        for order in orders:
            for order_product in order.order_products:
                product_id = order_product.product_id
                quantity = float(order_product.order_quantity)
                revenue = order_product.subtotal
                
                if product_id not in sales_data:
                    product = session.get(Product, product_id)
                    sales_data[product_id] = {
                        'product_id': product_id,
                        'product_name': product.name if product else 'Unknown',
                        'product_sku': product.sku if product else 'Unknown',
                        'total_quantity_sold': 0,
                        'total_revenue': 0,
                        'average_price': 0
                    }
                
                sales_data[product_id]['total_quantity_sold'] += quantity
                sales_data[product_id]['total_revenue'] += revenue
                total_products_sold += quantity
                total_revenue += revenue
        
        # Calculate average prices
        for product_data in sales_data.values():
            if product_data['total_quantity_sold'] > 0:
                product_data['average_price'] = product_data['total_revenue'] / product_data['total_quantity_sold']
        
        report = {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_orders': len(orders),
                'total_products_sold': total_products_sold,
                'total_revenue': total_revenue
            },
            'product_sales': list(sales_data.values())
        }
        
        return api_response(200, "Sales report generated", report)
        
    except Exception as e:
        return api_response(500, f"Error generating sales report: {str(e)}")
    
# def create_shop_earning(session, order: Order):
#     """Create shop earning record when order is completed"""
#     if order.order_status != OrderStatusEnum.COMPLETED or not order.shop_id:
#         return
    
#     # Calculate shop earning (order total - admin commission - delivery fee)
#     shop_earning = order.total - order.admin_commission_amount - (order.delivery_fee or 0)
    
#     earning = ShopEarning(
#         shop_id=order.shop_id,
#         order_id=order.id,
#         order_amount=order.total,
#         admin_commission=order.admin_commission_amount,
#         shop_earning=shop_earning
#     )
    
#     session.add(earning)