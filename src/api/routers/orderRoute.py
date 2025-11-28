# src/api/routes/orderRoute.py
import ast
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query
from sqlalchemy import select,func
from sqlmodel import SQLModel, Field,Relationship
from src.api.models.cart_model.cartModel import Cart
from src.api.core.utility import Print, uniqueSlugify
from src.api.core.operation import listop, updateOp
from src.api.core.response import api_response, raiseExceptions
from sqlalchemy.orm import selectinload, joinedload
from src.api.core.email_helper import send_email
from src.api.core.avatar_helper import get_user_avatar

from src.api.models.order_model.orderModel import (
    Order,
    OrderCartCreate,
    OrderCreate,
    OrderUpdate,
    OrderRead,
    OrderReadNested,
    OrderStatusUpdate,
    OrderProduct,
    OrderStatus,
    OrderStatusEnum,
    PaymentStatusEnum,
    OrderItemType,
    OrderProductCreate,
    OrderFromCartCreate,
    FulfillmentUserInfo
)
from src.api.models.product_model.productsModel import Product, ProductRead, ProductType
from src.api.models.product_model.variationOptionModel import VariationOption
from src.api.models.category_model import Category
from src.api.models.shop_model.shopsModel import Shop
from src.api.models.withdrawModel import ShopEarning
# NEW: Import tax and shipping models
from src.api.models.taxModel import Tax
from src.api.models.shipping_model.shippingModel import Shipping
from src.api.models.couponModel import Coupon, CouponType
from src.api.core.dependencies import (
    GetSession,
    requirePermission,
    requireSignin,
    isAuthenticated,
)
from datetime import datetime, timezone
import uuid
from decimal import Decimal
# Add this cancellation request model to your orderModel.py
class OrderCancelRequest(SQLModel):
    reason: Optional[str] = Field(default=None, max_length=500)
    notify_customer: bool = Field(default=True)

class OrderCancelResponse(SQLModel):
    message: str
    order_id: int
    status: str
    products_restocked: bool
    cancelled_at: datetime
    cancelled_by: Optional[int] = None

router = APIRouter(prefix="/order", tags=["Order"])


def generate_tracking_number():
    """Generate unique tracking number"""
    return f"TRK-{uuid.uuid4().hex[:12].upper()}"


def add_fulfillment_user_info(order_data, order, session):
    """
    Add fulfillment user information to order data if fullfillment_id > 0

    Args:
        order_data: OrderRead or OrderReadNested instance
        order: Order model instance
        session: Database session
    """
    if order.fullfillment_id and order.fullfillment_id > 0:
        from src.api.models.usersModel import User

        fulfillment_user = session.get(User, order.fullfillment_id)
        if fulfillment_user:
            # Get avatar using helper function
            avatar = get_user_avatar(fulfillment_user.image, fulfillment_user.name)

            order_data.fullfillment_user_info = FulfillmentUserInfo(
                id=fulfillment_user.id,
                name=fulfillment_user.name,
                email=fulfillment_user.email,
                avatar=avatar
            )
    return order_data


def get_product_snapshot(session, product_id: int) -> Dict[str, Any]:
    """Get product snapshot for order record"""
    product = session.get(Product, product_id)
    if not product:
        return {}

    # Get shop information for the product
    shop_name = None
    shop_slug = None
    if product.shop_id:
        shop = session.get(Shop, product.shop_id)
        if shop:
            shop_name = shop.name
            shop_slug = shop.slug

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
        "shop_id": product.shop_id,
        "shop_name": shop_name,
        "shop_slug": shop_slug,
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


def validate_product_availability(
    session, product_data: OrderProductCreate
) -> tuple[bool, str]:
    """Validate product availability based on type"""
    product = session.get(Product, product_data.product_id)
    if not product or not product.is_active:
        return False, "Product not found or inactive"

    # Validate that product belongs to the specified shop
    if product_data.shop_id and product.shop_id != product_data.shop_id:
        return False, f"Product does not belong to specified shop"

    # Set shop_id from product if not provided
    if not product_data.shop_id and product.shop_id:
        product_data.shop_id = product.shop_id

    if product_data.item_type == OrderItemType.SIMPLE:
        if product.quantity >= float(product_data.order_quantity) and product.in_stock:
            return True, "Available"
        else:
            return (
                False,
                f"Insufficient stock. Available: {product.quantity}, Requested: {product_data.order_quantity}",
            )

    elif product_data.item_type == OrderItemType.VARIABLE:
        if not product_data.variation_option_id:
            return False, "Variation option ID required for variable product"
        variation = session.get(VariationOption, product_data.variation_option_id)
        if (
            variation
            and variation.quantity >= float(product_data.order_quantity)
            and variation.is_active
        ):
            return True, "Available"
        else:
            available_qty = variation.quantity if variation else 0
            return (
                False,
                f"Insufficient variation stock. Available: {available_qty}, Requested: {product_data.order_quantity}",
            )

    return False, "Unknown product type"


def update_product_inventory(
    session, product_data: OrderProductCreate, operation: str = "deduct"
):
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

    elif (
        product_data.item_type == OrderItemType.VARIABLE
        and product_data.variation_option_id
    ):
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

                # FIXED: Recalculate total quantity from variations using scalar()
                total_variation_quantity = session.scalar(
                    select(func.sum(VariationOption.quantity)).where(
                        VariationOption.product_id == product_data.product_id
                    )
                ) or 0
                
                product.quantity = total_variation_quantity
                session.add(product)

            if variation.quantity <= 0:
                variation.is_active = False
            session.add(variation)


def calculate_admin_commission(
    session, product_id: int, subtotal_after_discount: float
) -> Decimal:
    """
    Calculate admin commission based on product's category commission rate
    Commission is calculated on the subtotal AFTER sale price discount is applied
    """
    try:
        product = session.exec(
            select(Product).where(Product.id == product_id)
        ).scalar_one_or_none()

        if not product or not product.category_id:
            return Decimal("0.00")

        category = session.get(Category, product.category_id)
        if not category or not category.admin_commission_rate:
            return Decimal("0.00")

        # Calculate commission on the discounted subtotal
        commission_amount = subtotal_after_discount * (
            category.admin_commission_rate / 100
        )

        return Decimal(str(round(commission_amount, 2)))

    except (ValueError, TypeError) as e:
        Print(f"Error calculating commission: {e}")
        return Decimal("0.00")


def update_order_status_history(session, order_id: int, status_field: str):
    """Update order status history when order status changes"""
    # Get the OrderStatus record properly
    order_status = session.exec(
        select(OrderStatus).where(OrderStatus.order_id == order_id)
    ).first()
    
    # Handle Row object if returned
    if order_status and hasattr(order_status, '_mapping'):
        order_status = order_status._mapping.get('OrderStatus') or order_status._mapping.get(OrderStatus)
        if not order_status:
            # Try to find OrderStatus in mapping values
            for value in order_status._mapping.values():
                if isinstance(value, OrderStatus):
                    order_status = value
                    break

    if not order_status:
        # Create new order status record if it doesn't exist
        order_status = OrderStatus(order_id=order_id)
        session.add(order_status)
        session.flush()  # Flush to get the ID

    # Now set the attribute on the model instance
    setattr(order_status, status_field, datetime.now())
    session.add(order_status)


def validate_tax_shipping_coupon(session, tax_id: Optional[int], shipping_id: Optional[int], coupon_id: Optional[int], order_amount: float) -> tuple[bool, str, Dict[str, Any]]:
    """
    Validate tax, shipping, and coupon with enhanced coupon validation
    Returns: (is_valid, error_message, calculation_data)
    """
    calculation_data = {
        'tax_rate': 0.0,
        'tax_amount': 0.0,
        'shipping_amount': 0.0,
        'coupon_discount': 0.0,
        'coupon_type': None
    }
    
    # Validate tax
    if tax_id:
        tax = session.get(Tax, tax_id)
        if not tax:
            return False, "Tax not found", calculation_data
        if not tax.is_global and not tax.is_active:
            return False, "Tax is not active", calculation_data
        calculation_data['tax_rate'] = tax.rate
    
    # Validate shipping
    if shipping_id:
        shipping = session.get(Shipping, shipping_id)
        if not shipping:
            return False, "Shipping not found", calculation_data
        if not shipping.is_active:
            return False, "Shipping is not active", calculation_data
        calculation_data['shipping_amount'] = shipping.amount
    
    # Validate coupon with enhanced checks
    if coupon_id:
        coupon = session.get(Coupon, coupon_id)
        if not coupon:
            return False, "Coupon not found", calculation_data
        
        # Check if coupon is active
        now = datetime.now()
        if now < coupon.active_from or now > coupon.expire_at:
            return False, "Coupon is not active", calculation_data
        
        # Check minimum cart amount
        if order_amount < coupon.minimum_cart_amount:
            return False, f"Order amount must be at least {coupon.minimum_cart_amount} to use this coupon", calculation_data
        
        calculation_data['coupon_type'] = coupon.type
        
        # Calculate coupon discount based on type
        if coupon.type == CouponType.FIXED:
            calculation_data['coupon_discount'] = min(coupon.amount, order_amount)
        elif coupon.type == CouponType.PERCENTAGE:
            calculation_data['coupon_discount'] = order_amount * (coupon.amount / 100)
        elif coupon.type == CouponType.FREE_SHIPPING:
            calculation_data['coupon_discount'] = calculation_data['shipping_amount']
            calculation_data['shipping_amount'] = 0.0
    
    return True, "Validation successful", calculation_data


def calculate_product_discount(price: float, sale_price: Optional[float], quantity: float) -> float:
    """Calculate product-level discount"""
    if sale_price and sale_price > 0 and sale_price < price:
        return (price - sale_price) * quantity
    return 0.0


def calculate_item_tax(subtotal: float, tax_rate: float) -> float:
    """Calculate tax for individual item"""
    return subtotal * (tax_rate / 100)


@router.post("/cartcreate")
def create(request: OrderCartCreate, session: GetSession, user: isAuthenticated = None):
    cart_items = request.cart or []
    shipping_address = request.shipping_address
    
    # ✅ 1. Validate cart data
    if not isinstance(cart_items, list) or not cart_items:
        return api_response(400, "Cart cannot be empty")

    product_ids = [
        item.product_id for item in cart_items if item.product_id and item.product_id
    ]

    if not product_ids:
        return api_response(400, "Each cart item must include a valid product ID")

    # ✅ 2. Validate products exist in db
    products = (
        session.exec(select(Product).where(Product.id.in_(product_ids))).scalars().all()
    )
    if len(products) != len(product_ids):
        found = {p.id for p in products}
        missing = [pid for pid in product_ids if pid not in found]
        return api_response(404, f"Product(s) not found: {missing}")

    # ✅ 3. Validate carts if user is authenticated
    carts = []
    if user:
        carts = (
            session.exec(
                select(Cart)
                .where(Cart.user_id == user["id"])
                .where(Cart.product_id.in_(product_ids))
            )
            .scalars()
            .all()
        )
        if len(carts) != len(product_ids):
            found_ids = {c.product_id for c in carts}
            missing = [pid for pid in product_ids if pid not in found_ids]
            return api_response(
                404, f"Cart item(s) not found for product(s): {missing}"
            )

    # ✅ 4. Calculate initial totals and validate variable products
    subtotal_amount = 0.0
    total_product_discount = 0.0
    validation_errors = []
    
    # NEW: Calculate initial subtotal for tax/shipping/coupon validation
    initial_calculation = {}
    for item in cart_items:
        product = next((p for p in products if p.id == item.product_id), None)
        if not product:
            validation_errors.append(f"Product {item.product_id} not found")
            continue
        
        try:
            quantity = float(item.quantity)
        except (ValueError, TypeError):
            validation_errors.append(f"Invalid quantity for product {product.name}: {item.quantity}")
            continue
            
        # Handle variable products
        if item.variation_option_id:
            variation = session.get(VariationOption, item.variation_option_id)
            if not variation:
                validation_errors.append(f"Variation option {item.variation_option_id} not found")
                continue
                
            if variation.product_id != product.id:
                validation_errors.append(f"Variation {item.variation_option_id} does not belong to product {product.id}")
                continue
                
            # Check variation stock
            if variation.quantity < quantity:
                validation_errors.append(f"Insufficient stock for variation {variation.title}. Available: {variation.quantity}, Requested: {quantity}")
                continue
                
            price = float(variation.price)
            sale_price = float(variation.sale_price) if variation.sale_price and variation.sale_price > 0 else None
        else:
            # Handle simple product
            if product.quantity < quantity:
                validation_errors.append(f"Insufficient stock for {product.name}. Available: {product.quantity}, Requested: {quantity}")
                continue
                
            price = float(product.price)
            sale_price = float(product.sale_price) if product.sale_price and product.sale_price > 0 else None
        
        # Calculate product discount
        item_discount = calculate_product_discount(price, sale_price, quantity)
        total_product_discount += item_discount
        
        # Use sale price if available, otherwise use regular price
        final_price = sale_price if sale_price and sale_price > 0 else price
        subtotal_amount += final_price * quantity

    if validation_errors:
        return api_response(400, "Product validation failed", {"errors": validation_errors})

    # NEW: Validate tax, shipping, and coupon
    is_valid, error_msg, calc_data = validate_tax_shipping_coupon(
        session, request.tax_id, request.shipping_id, request.coupon_id, subtotal_amount
    )
    if not is_valid:
        return api_response(400, error_msg)

    # NEW: Calculate final amounts with tax, shipping, and coupon
    tax_amount = subtotal_amount * (calc_data['tax_rate'] / 100)
    shipping_amount = calc_data['shipping_amount']
    coupon_discount = calc_data['coupon_discount']
    
    # Calculate final total
    final_total = subtotal_amount + tax_amount + shipping_amount - coupon_discount
    
    # Ensure total doesn't go below zero
    final_total = max(0, final_total)

    # ✅ 5. Build order fields with NEW fields
    tracking_number = generate_tracking_number()
    order = Order(
        tracking_number=tracking_number,
        customer_id=user["id"] if user else None,
        customer_contact=shipping_address.get("phone"),
        customer_name=shipping_address.get("name"),
        amount=subtotal_amount,  # Subtotal before discounts/taxes
        sales_tax=tax_amount,
        total=final_total,
        discount=total_product_discount,  # Total product discounts
        coupon_discount=coupon_discount,  # NEW: Coupon discount
        shipping_address=shipping_address,
        billing_address=shipping_address,  # same for now
        # NEW: Add tax_id, shipping_id, coupon_id
        tax_id=request.tax_id,
        shipping_id=request.shipping_id,
        coupon_id=request.coupon_id,
        delivery_fee=shipping_amount,
        order_status="order-pending",
        payment_status="payment-cash-on-delivery",
        language="en",
    )

    session.add(order)
    session.flush()

    # 🔥 NEW: Initialize total admin commission
    total_admin_commission = Decimal("0.00")

    # ✅ 6. Create order products with enhanced calculations
    order_products = []
    for item in cart_items:
        product = next((p for p in products if p.id == item.product_id), None)
        if not product:
            continue

        try:
            quantity = float(item.quantity)
        except (ValueError, TypeError):
            continue

        # Determine product type and pricing
        item_type = OrderItemType.VARIABLE if item.variation_option_id else OrderItemType.SIMPLE
        
        # Create product and variation snapshots
        product_snapshot = get_product_snapshot(session, product.id)
        variation_snapshot = None
        
        if item_type == OrderItemType.VARIABLE:
            variation = session.get(VariationOption, item.variation_option_id)
            if not variation:
                continue
                
            price = float(variation.price)
            sale_price = float(variation.sale_price) if variation.sale_price and variation.sale_price > 0 else None
            
            # Create variation snapshot
            variation_snapshot = get_variation_snapshot(session, item.variation_option_id)
            variation_data = {
                "id": variation.id,
                "title": variation.title,
                "options": variation.options,
            } if variation else None
        else:
            price = float(product.price)
            sale_price = float(product.sale_price) if product.sale_price and product.sale_price > 0 else None
            variation_data = None

        # Calculate item-level values
        final_price = sale_price if sale_price and sale_price > 0 else price
        subtotal = final_price * quantity
        item_discount = calculate_product_discount(price, sale_price, quantity)
        item_tax = calculate_item_tax(subtotal, calc_data['tax_rate'])

        # Calculate admin commission on subtotal (after sale price discount)
        admin_commission = calculate_admin_commission(
            session, product.id, subtotal
        )
        total_admin_commission += admin_commission
        
        # Create OrderProduct with enhanced fields
        op = OrderProduct(
            order_id=order.id,
            product_id=product.id,
            variation_option_id=item.variation_option_id,
            order_quantity=str(quantity),
            unit_price=price,  # Original price
            sale_price=sale_price,  # NEW: Sale price
            subtotal=subtotal,
            item_discount=item_discount,  # NEW: Item discount
            item_tax=item_tax,  # NEW: Item tax
            admin_commission=admin_commission,
            item_type=item_type,
            variation_data=variation_data,
            shop_id=product.shop_id,
            product_snapshot=product_snapshot,
            variation_snapshot=variation_snapshot,
        )
        order_products.append(op)

    session.add_all(order_products)
    
    # Update order with total admin commission
    order.admin_commission_amount = total_admin_commission
    session.add(order)
    
    # Create initial order status history
    order_status = OrderStatus(order_id=order.id, order_pending_date=datetime.now())
    session.add(order_status)
    
    # Update inventory using the proper update_product_inventory function
    for item in cart_items:
        product = next((p for p in products if p.id == item.product_id), None)
        if not product:
            continue
        
        # Create OrderProductCreate object for inventory update
        product_data = OrderProductCreate(
            product_id=item.product_id,
            variation_option_id=item.variation_option_id,
            order_quantity=str(item.quantity),
            unit_price=0.0,
            subtotal=0.0,
            item_type=OrderItemType.VARIABLE if item.variation_option_id else OrderItemType.SIMPLE,
            shop_id=product.shop_id,
        )
        
        # Use the centralized update_product_inventory function
        update_product_inventory(session, product_data, operation="deduct")

    # ✅ 7. Clear user cart if authenticated
    if user and carts:
        for cart in carts:
            session.delete(cart)

    try:
        session.commit()
        session.refresh(order)

        # Send order confirmation email
        try:
            send_email(
                to_email=shipping_address.get("email") or order.customer_contact,
                email_template_id=5,  # Use appropriate template ID for order confirmation
                replacements={
                    "customer_name": order.customer_name,
                    "tracking_number": tracking_number,
                    "order_id": order.id,
                    "amount": order.amount,
                    "total": order.total,
                    "delivery_fee": order.delivery_fee,
                },
                session=session
            )
        except Exception as e:
            # Log email error but don't fail order creation
            Print(f"Failed to send order confirmation email: {e}")

        return api_response(
            201,
            "Order created successfully",
            {
                "order_id": order.id,
                "tracking_number": tracking_number,
                "amount": order.amount,
                "total": order.total,
                "discount": order.discount,
                "coupon_discount": order.coupon_discount,
                "sales_tax": order.sales_tax,
                "delivery_fee": order.delivery_fee,
            },
        )
    except Exception as e:
        session.rollback()
        Print(f"Order creation error: {e}")
        return api_response(500, "Failed to create order")
    
@router.post("/create-from-cart")
def create_order_from_cart(
    request: OrderFromCartCreate,
    session: GetSession, 
    user: requireSignin
):
    """
    Create order from user's cart items and clear cart after successful order creation
    """
    user_id = user.get("id")
    shipping_address = request.shipping_address
    
    # ✅ 1. Validate required fields
    if not shipping_address:
        return api_response(400, "Shipping address is required")
    
    required_address_fields = ["name", "phone", "street", "city", "country"]
    missing_fields = [field for field in required_address_fields if not shipping_address.get(field)]
    if missing_fields:
        return api_response(400, f"Missing required shipping address fields: {', '.join(missing_fields)}")
    
    # ✅ 2. Get user's cart items from cart table - handle Row objects
    try:
        Print(f"🔍 Fetching cart items for user_id: {user_id}")
        cart_stmt = select(Cart).where(Cart.user_id == user_id)
        cart_result = session.exec(cart_stmt)
        cart_items = cart_result.all()
        
        Print(f"✅ Found {len(cart_items)} cart items for user {user_id}")
        
        if not cart_items:
            return api_response(400, "Cart is empty")
        
        # Debug: Check the type of cart items
        Print(f"📋 Cart items type: {type(cart_items)}")
        Print(f"📋 First cart item type: {type(cart_items[0]) if cart_items else 'None'}")
        
        # Handle Row objects - extract Cart model instances
        processed_cart_items = []
        for i, item in enumerate(cart_items):
            Print(f"🛒 Processing cart item {i}: {item}")
            
            # For Row objects from SQLAlchemy, we need to extract the actual model instance
            cart_obj = None
            
            if hasattr(item, '_mapping'):
                # This is a Row object, get the Cart model from _mapping
                mapping = dict(item._mapping)
                Print(f"   📋 Row _mapping keys: {list(mapping.keys())}")
                
                # The Cart object is typically stored with the model class as key
                if 'Cart' in mapping:
                    cart_obj = mapping['Cart']
                    Print(f"   ✅ Extracted Cart object from _mapping['Cart']")
                elif Cart in mapping:
                    cart_obj = mapping[Cart]
                    Print(f"   ✅ Extracted Cart object from _mapping[Cart]")
                else:
                    # Try to get the first value if it's a Cart instance
                    for key, value in mapping.items():
                        if isinstance(value, Cart):
                            cart_obj = value
                            Print(f"   ✅ Found Cart object in _mapping")
                            break
            elif isinstance(item, Cart):
                # Already a Cart instance
                cart_obj = item
                Print(f"   ✅ Item is already a Cart instance")
            
            if not cart_obj:
                Print(f"   ❌ Could not extract Cart object from item")
                continue
            
            # Now extract data from the Cart object
            cart_data = {
                'id': cart_obj.id,
                'product_id': cart_obj.product_id,
                'user_id': cart_obj.user_id,
                'shop_id': cart_obj.shop_id,
                'quantity': cart_obj.quantity,
                'variation_option_id': cart_obj.variation_option_id,
                'created_at': cart_obj.created_at,
                'updated_at': cart_obj.updated_at
            }
            
            processed_cart_items.append(cart_data)
            Print(f"   📋 Final cart data: product_id={cart_data['product_id']}, quantity={cart_data['quantity']}")
        
        Print(f"✅ Processed {len(processed_cart_items)} cart items")
                
    except Exception as e:
        Print(f"❌ Error fetching cart items: {str(e)}")
        import traceback
        Print(f"📋 Traceback: {traceback.format_exc()}")
        return api_response(500, f"Error fetching cart items: {str(e)}")
    
    if not processed_cart_items:
        return api_response(400, "No valid cart items found")
    
    # ✅ 3. Extract product IDs from processed cart items
    product_ids = []
    valid_cart_items = []
    
    Print(f"🔍 Extracting product IDs from {len(processed_cart_items)} processed cart items...")
    
    for i, cart_data in enumerate(processed_cart_items):
        product_id = cart_data.get('product_id')
        Print(f"   Processed cart item {i}: product_id = {product_id}")
        
        if product_id:
            product_ids.append(product_id)
            valid_cart_items.append(cart_data)
            Print(f"   ✅ Added product_id {product_id} to list")
        else:
            Print(f"   ❌ Processed cart item {i} has no product_id")
    
    Print(f"📋 Final product_ids list: {product_ids}")
    Print(f"📋 Valid cart items count: {len(valid_cart_items)}")
    
    if not product_ids:
        Print("❌ No valid product IDs found in cart items")
        return api_response(400, "No valid products found in cart")
    
    # ✅ 4. Get products from database
    try:
        Print(f"🔍 Fetching products from database for IDs: {product_ids}")
        products_stmt = select(Product).where(Product.id.in_(product_ids))
        products_result = session.exec(products_stmt)
        products_rows = products_result.all()
        
        # Process product rows similarly
        products = []
        for product_row in products_rows:
            if hasattr(product_row, '_mapping'):
                # Extract Product object from Row
                mapping = dict(product_row._mapping)
                product_obj = None
                
                if 'Product' in mapping:
                    product_obj = mapping['Product']
                elif Product in mapping:
                    product_obj = mapping[Product]
                else:
                    for key, value in mapping.items():
                        if isinstance(value, Product):
                            product_obj = value
                            break
                
                if product_obj:
                    products.append(product_obj)
            elif isinstance(product_row, Product):
                products.append(product_row)
        
        Print(f"✅ Found {len(products)} products in database")
        
        # Debug each product found
        for i, product in enumerate(products):
            Print(f"   Product {i}: ID={product.id}, Name='{product.name}', Active={product.is_active}, Price={product.price}")
            
    except Exception as e:
        Print(f"❌ Error fetching products: {str(e)}")
        return api_response(500, f"Error fetching products: {str(e)}")
    
    # Create product lookup dictionary
    product_dict = {product.id: product for product in products}
    Print(f"📋 Product lookup dictionary keys: {list(product_dict.keys())}")
    
    # ✅ 5. Validate all cart items and calculate initial totals
    subtotal_amount = 0.0
    total_product_discount = 0.0
    validation_errors = []
    order_products_data = []
    
    Print(f"🔍 Validating {len(valid_cart_items)} cart items...")
    
    for i, cart_data in enumerate(valid_cart_items):
        product_id = cart_data['product_id']
        Print(f"   Processing cart item {i}: product_id={product_id}")
        
        product = product_dict.get(product_id)
        
        if not product:
            error_msg = f"Product {product_id} not found in database"
            Print(f"   ❌ {error_msg}")
            validation_errors.append(error_msg)
            continue
        
        Print(f"   ✅ Product found: {product.name} (ID: {product.id})")
        
        if not product.is_active:
            error_msg = f"Product {product.name} is not active"
            Print(f"   ❌ {error_msg}")
            validation_errors.append(error_msg)
            continue
        
        Print(f"   ✅ Product is active")
        
        # Get variation_option_id from cart data
        variation_option_id = cart_data.get('variation_option_id')
        Print(f"   Variation option ID: {variation_option_id}")
        
        # Get quantity from cart data
        quantity = None
        try:
            quantity = float(cart_data['quantity'])
            Print(f"   Quantity: {quantity}")
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid quantity for product {product.name}: {cart_data['quantity']} - Error: {str(e)}"
            Print(f"   ❌ {error_msg}")
            validation_errors.append(error_msg)
            continue
        
        if not quantity or quantity <= 0:
            error_msg = f"Invalid quantity for product {product.name}: {quantity}"
            Print(f"   ❌ {error_msg}")
            validation_errors.append(error_msg)
            continue
        
        Print(f"   ✅ Quantity is valid: {quantity}")
        
        # Determine product type and validate availability
        item_type = OrderItemType.VARIABLE if variation_option_id else OrderItemType.SIMPLE
        Print(f"   Item type: {item_type}")
        
        # Validate variable products
        if item_type == OrderItemType.VARIABLE:
            Print(f"   🔍 Validating variable product...")
            variation = session.get(VariationOption, variation_option_id)
            if not variation:
                error_msg = f"Variation option {variation_option_id} not found"
                Print(f"   ❌ {error_msg}")
                validation_errors.append(error_msg)
                continue
            
            if variation.product_id != product.id:
                error_msg = f"Variation {variation_option_id} does not belong to product {product.id}"
                Print(f"   ❌ {error_msg}")
                validation_errors.append(error_msg)
                continue
            
            # Check variation stock
            variation_quantity = variation.quantity
            if variation_quantity < quantity:
                error_msg = f"Insufficient stock for variation {variation.title}. Available: {variation_quantity}, Requested: {quantity}"
                Print(f"   ❌ {error_msg}")
                validation_errors.append(error_msg)
                continue
            
            Print(f"   ✅ Variation stock is sufficient")
            
            # Get variation prices
            price = float(variation.price)
            sale_price = float(variation.sale_price) if variation.sale_price and variation.sale_price > 0 else None
            Print(f"   Variation price: {price}, sale_price: {sale_price}")
            
            variation_data = {
                "id": variation.id,
                "title": variation.title,
                "options": variation.options,
            }
            
        else:
            # Validate simple product
            Print(f"   🔍 Validating simple product...")
            product_quantity = product.quantity
            if product_quantity < quantity:
                error_msg = f"Insufficient stock for {product.name}. Available: {product_quantity}, Requested: {quantity}"
                Print(f"   ❌ {error_msg}")
                validation_errors.append(error_msg)
                continue
            
            Print(f"   ✅ Product stock is sufficient")
            
            # Get product prices
            price = float(product.price)
            sale_price = float(product.sale_price) if product.sale_price and product.sale_price > 0 else None
            Print(f"   Product price: {price}, sale_price: {sale_price}")
            variation_data = None
        
        # Calculate product discount
        item_discount = calculate_product_discount(price, sale_price, quantity)
        total_product_discount += item_discount
        
        # Use sale price if available, otherwise use regular price
        final_price = sale_price if sale_price and sale_price > 0 else price
        subtotal = final_price * quantity
        subtotal_amount += subtotal
        
        Print(f"   💰 Price calculations: final_price={final_price}, subtotal={subtotal}, item_discount={item_discount}")
        
        # Prepare order product data
        order_product_data = OrderProductCreate(
            product_id=product.id,
            variation_option_id=variation_option_id,
            order_quantity=str(quantity),
            unit_price=price,  # Original price
            subtotal=subtotal,
            item_type=item_type,
            variation_data=variation_data,
            shop_id=product.shop_id,
        )
        order_products_data.append(order_product_data)
        Print(f"   ✅ Successfully added product {product.name} to order products")
    
    Print(f"📋 Validation completed. Errors: {len(validation_errors)}, Order products: {len(order_products_data)}")
    
    if validation_errors:
        Print(f"❌ Validation errors: {validation_errors}")
        return api_response(400, "Cart validation failed", {"errors": validation_errors})

    # ✅ 6. Validate tax, shipping, and coupon
    is_valid, error_msg, calc_data = validate_tax_shipping_coupon(
        session, request.tax_id, request.shipping_id, request.coupon_id, subtotal_amount
    )
    if not is_valid:
        return api_response(400, error_msg)

    # ✅ 7. Calculate final amounts with tax, shipping, and coupon
    tax_amount = subtotal_amount * (calc_data['tax_rate'] / 100)
    shipping_amount = calc_data['shipping_amount']
    coupon_discount = calc_data['coupon_discount']
    
    # Calculate final total
    final_total = subtotal_amount + tax_amount + shipping_amount - coupon_discount
    
    # Ensure total doesn't go below zero
    final_total = max(0, final_total)

    # ✅ 8. Create order with enhanced fields
    tracking_number = generate_tracking_number()
    
    order = Order(
        tracking_number=tracking_number,
        customer_id=user_id,
        customer_contact=shipping_address.get("phone"),
        customer_name=shipping_address.get("name"),
        amount=subtotal_amount,  # Subtotal before discounts/taxes
        sales_tax=tax_amount,
        total=final_total,
        discount=total_product_discount,  # Total product discounts
        coupon_discount=coupon_discount,  # Coupon discount
        shipping_address=shipping_address,
        billing_address=shipping_address,  # Same as shipping for now
        # Add tax_id, shipping_id, coupon_id
        tax_id=request.tax_id,
        shipping_id=request.shipping_id,
        coupon_id=request.coupon_id,
        delivery_fee=shipping_amount,
        order_status=OrderStatusEnum.PENDING.value,
        payment_status=PaymentStatusEnum.PENDING.value,
        language="en",
    )
    
    session.add(order)
    session.flush()
    
    # ✅ 9. Create order products with snapshots and commissions
    total_admin_commission = Decimal("0.00")
    created_order_products = []
    
    for product_data in order_products_data:
        product = product_dict.get(product_data.product_id)
        if not product:
            continue
            
        # Create product snapshots
        product_snapshot = get_product_snapshot(session, product_data.product_id)
        variation_snapshot = None
        if product_data.variation_option_id:
            variation_snapshot = get_variation_snapshot(session, product_data.variation_option_id)

        # Calculate item-level values
        quantity = float(product_data.order_quantity)
        item_discount = calculate_product_discount(
            product_data.unit_price,
            product.sale_price if product.sale_price and product.sale_price > 0 else None,
            quantity
        )
        item_tax = calculate_item_tax(product_data.subtotal, calc_data['tax_rate'])

        # Calculate admin commission on subtotal (after sale price discount)
        admin_commission = calculate_admin_commission(
            session,
            product_data.product_id,
            product_data.subtotal
        )
        total_admin_commission += admin_commission
        
        # Create order product with enhanced fields
        order_product = OrderProduct(
            order_id=order.id,
            product_id=product_data.product_id,
            variation_option_id=product_data.variation_option_id,
            order_quantity=product_data.order_quantity,
            unit_price=product_data.unit_price,
            sale_price=product.sale_price if product.sale_price and product.sale_price > 0 else None,
            subtotal=product_data.subtotal,
            item_discount=item_discount,
            item_tax=item_tax,
            admin_commission=admin_commission,
            item_type=product_data.item_type,
            variation_data=product_data.variation_data,
            shop_id=product_data.shop_id,
            product_snapshot=product_snapshot,
            variation_snapshot=variation_snapshot,
        )
        session.add(order_product)
        created_order_products.append(order_product)
        
        # Update inventory
        update_product_inventory(session, product_data, "deduct")
    
    # ✅ 10. Update order with total admin commission
    order.admin_commission_amount = total_admin_commission
    session.add(order)
    
    # ✅ 11. Create initial order status history
    order_status = OrderStatus(order_id=order.id, order_pending_date=datetime.now())
    session.add(order_status)
    
    # ✅ 12. CLEAR USER'S CART after successful order creation
    try:
        # Delete all cart items for this user
        delete_stmt = select(Cart).where(Cart.user_id == user_id)
        user_cart_items_result = session.exec(delete_stmt).all()
        
        # Extract Cart objects from Row objects
        cart_items_to_delete = []
        for item in user_cart_items_result:
            cart_obj = None
            
            if hasattr(item, '_mapping'):
                mapping = dict(item._mapping)
                if 'Cart' in mapping:
                    cart_obj = mapping['Cart']
                elif Cart in mapping:
                    cart_obj = mapping[Cart]
                else:
                    for key, value in mapping.items():
                        if isinstance(value, Cart):
                            cart_obj = value
                            break
            elif isinstance(item, Cart):
                cart_obj = item
            
            if cart_obj:
                cart_items_to_delete.append(cart_obj)
        
        # Delete all cart items
        for cart_item in cart_items_to_delete:
            session.delete(cart_item)
        
        # Commit all changes (order creation + cart clearance)
        session.commit()
        
        Print(f"✅ Successfully cleared {len(cart_items_to_delete)} items from cart")
        
    except Exception as e:
        # Rollback if cart clearance fails
        session.rollback()
        Print(f"❌ Error clearing cart: {str(e)}")
        import traceback
        Print(f"📋 Traceback: {traceback.format_exc()}")
        return api_response(500, f"Order created but failed to clear cart: {str(e)}")
    
    # ✅ 13. Prepare response data
    products_data = []
    for product in products:
        product_data = ProductRead.model_validate(product).model_dump()
        # Include variation information if applicable
        cart_item_data = next((item for item in valid_cart_items if item['product_id'] == product.id), None)
        if cart_item_data and cart_item_data.get('variation_option_id'):
            variation = session.get(VariationOption, cart_item_data['variation_option_id'])
            if variation:
                product_data["selected_variation"] = {
                    "id": variation.id,
                    "title": variation.title,
                    "options": variation.options,
                }
        products_data.append(product_data)

    # Send order confirmation email
    try:
        send_email(
            to_email=shipping_address.get("email") or order.customer_contact,
            email_template_id=5,  # Use appropriate template ID for order confirmation
            replacements={
                "customer_name": order.customer_name,
                "tracking_number": tracking_number,
                "order_id": order.id,
                "amount": order.amount,
                "total": order.total,
                "delivery_fee": order.delivery_fee,
            },
            session=session
        )
    except Exception as e:
        # Log email error but don't fail order creation
        Print(f"Failed to send order confirmation email: {e}")

    return api_response(
        201,
        "Order created successfully from cart and cart cleared",
        {
            "order_id": order.id,
            "tracking_number": tracking_number,
            "amount": order.amount,
            "total": order.total,
            "discount": order.discount,
            "coupon_discount": order.coupon_discount,
            "sales_tax": order.sales_tax,
            "delivery_fee": order.delivery_fee,
            "items": len(created_order_products),
            "products": products_data,
            "cart_cleared": True,
            "cart_items_removed": len(cart_items_to_delete),
        },
    )

@router.post("/create")
def create_order(request: OrderCreate, session: GetSession, user: isAuthenticated = None):
    """Create direct order with enhanced tax, shipping, and coupon calculations"""
    
    # ✅ 1. Validate order products
    if not request.order_products:
        return api_response(400, "Order products cannot be empty")

    # ✅ 2. Validate products and calculate initial totals
    subtotal_amount = 0.0
    total_product_discount = 0.0
    validation_errors = []
    
    for op_request in request.order_products:
        is_available, message = validate_product_availability(session, op_request)
        if not is_available:
            validation_errors.append(f"Product {op_request.product_id}: {message}")
            continue
            
        product = session.get(Product, op_request.product_id)
        if not product:
            validation_errors.append(f"Product {op_request.product_id} not found")
            continue
            
        try:
            quantity = float(op_request.order_quantity)
        except (ValueError, TypeError):
            validation_errors.append(f"Invalid quantity for product {product.name}: {op_request.order_quantity}")
            continue
            
        # Calculate product discount
        item_discount = calculate_product_discount(
            op_request.unit_price, 
            product.sale_price if product.sale_price and product.sale_price > 0 else None, 
            quantity
        )
        total_product_discount += item_discount
        subtotal_amount += op_request.subtotal

    if validation_errors:
        return api_response(400, "Product validation failed", {"errors": validation_errors})

    # NEW: Validate tax, shipping, and coupon
    is_valid, error_msg, calc_data = validate_tax_shipping_coupon(
        session, request.tax_id, request.shipping_id, request.coupon_id, subtotal_amount
    )
    if not is_valid:
        return api_response(400, error_msg)

    # NEW: Calculate final amounts with tax, shipping, and coupon
    tax_amount = subtotal_amount * (calc_data['tax_rate'] / 100)
    shipping_amount = calc_data['shipping_amount']
    coupon_discount = calc_data['coupon_discount']
    
    # Calculate final total
    final_total = subtotal_amount + tax_amount + shipping_amount - coupon_discount
    
    # Ensure total doesn't go below zero
    final_total = max(0, final_total)

    # ✅ 3. Create order with enhanced fields
    tracking_number = generate_tracking_number()
    order = Order(
        tracking_number=tracking_number,
        customer_id=request.customer_id or (user["id"] if user else None),
        customer_contact=request.customer_contact,
        customer_name=request.customer_name,
        amount=subtotal_amount,
        sales_tax=tax_amount,
        total=final_total,
        discount=total_product_discount,
        coupon_discount=coupon_discount,  # NEW: Coupon discount
        payment_gateway=request.payment_gateway,
        shipping_address=request.shipping_address,
        billing_address=request.billing_address,
        logistics_provider=request.logistics_provider,
        delivery_fee=shipping_amount,
        delivery_time=request.delivery_time,
        # NEW: Add tax_id, shipping_id, coupon_id
        tax_id=request.tax_id,
        shipping_id=request.shipping_id,
        coupon_id=request.coupon_id,
        order_status="order-pending",
        payment_status="payment-pending",
        language="en",
    )

    session.add(order)
    session.flush()

    # ✅ 4. Create order products with enhanced calculations
    total_admin_commission = Decimal("0.00")
    order_products = []
    
    for op_request in request.order_products:
        product = session.get(Product, op_request.product_id)
        if not product:
            continue
            
        try:
            quantity = float(op_request.order_quantity)
        except (ValueError, TypeError):
            continue
            
        # Create product snapshot
        product_snapshot = get_product_snapshot(session, product.id)
        
        # Calculate item-level values
        item_discount = calculate_product_discount(
            op_request.unit_price,
            product.sale_price if product.sale_price and product.sale_price > 0 else None,
            quantity
        )
        item_tax = calculate_item_tax(op_request.subtotal, calc_data['tax_rate'])

        # Calculate admin commission on subtotal (after sale price discount)
        admin_commission = calculate_admin_commission(
            session, product.id, op_request.subtotal
        )
        total_admin_commission += admin_commission
        
        # Create OrderProduct
        op = OrderProduct(
            order_id=order.id,
            product_id=op_request.product_id,
            variation_option_id=op_request.variation_option_id,
            order_quantity=op_request.order_quantity,
            unit_price=op_request.unit_price,
            sale_price=product.sale_price if product.sale_price and product.sale_price > 0 else None,
            subtotal=op_request.subtotal,
            item_discount=item_discount,
            item_tax=item_tax,
            admin_commission=admin_commission,
            item_type=op_request.item_type,
            variation_data=op_request.variation_data,
            shop_id=product.shop_id,
            product_snapshot=product_snapshot,
        )
        order_products.append(op)
        
        # Update inventory
        update_product_inventory(session, op_request, operation="deduct")

    session.add_all(order_products)
    
    # Update order with total admin commission
    order.admin_commission_amount = total_admin_commission
    session.add(order)
    
    # Create initial order status history
    order_status = OrderStatus(order_id=order.id, order_pending_date=datetime.now())
    session.add(order_status)

    try:
        session.commit()
        return api_response(
            201,
            "Order created successfully",
            {
                "order_id": order.id,
                "tracking_number": tracking_number,
                "amount": order.amount,
                "total": order.total,
                "discount": order.discount,
                "coupon_discount": order.coupon_discount,
                "sales_tax": order.sales_tax,
                "delivery_fee": order.delivery_fee,
            },
        )
    except Exception as e:
        session.rollback()
        Print(f"Order creation error: {e}")
        return api_response(500, "Failed to create order")


@router.put("/update/{id}")
def update(id: int, request: OrderUpdate, session: GetSession, user: requireSignin):
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
    create_shop_earning(session, order)
    return api_response(
        200, "Order Updated Successfully", OrderReadNested.model_validate(order)
    )


@router.patch("/{id}/status")
def update_status(
    id: int, request: OrderStatusUpdate, session: GetSession, user: requireSignin
):
    order = session.get(Order, id)
    raiseExceptions((order, 404, "Order not found"))

    # Handle inventory restoration for cancelled/refunded orders
    if request.order_status in [
        OrderStatusEnum.CANCELLED,
        OrderStatusEnum.REFUNDED,
    ] and order.order_status not in [
        OrderStatusEnum.CANCELLED,
        OrderStatusEnum.REFUNDED,
    ]:

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
    create_shop_earning(session, order)

    # Send order status update email
    try:
        # Get user email if customer exists
        customer_email = None
        if order.customer_id:
            from src.api.models.usersModel import User
            customer = session.get(User, order.customer_id)
            if customer:
                customer_email = customer.email

        if customer_email or order.customer_contact:
            send_email(
                to_email=customer_email or order.customer_contact,
                email_template_id=6,  # Use appropriate template ID for order status update
                replacements={
                    "customer_name": order.customer_name,
                    "tracking_number": order.tracking_number,
                    "order_id": order.id,
                    "order_status": request.order_status,
                    "payment_status": request.payment_status or order.payment_status,
                },
                session=session
            )
    except Exception as e:
        # Log email error but don't fail status update
        Print(f"Failed to send order status update email: {e}")

    return api_response(
        200, "Order Status Updated Successfully", OrderRead.model_validate(order)
    )


@router.get("/read/{id}", response_model=OrderReadNested)
def get(id: int, session: GetSession, user: requireSignin):
    order = session.get(Order, id)
    print(f"order:{order}")
    raiseExceptions((order, 404, "Order not found"))

    # Enhance order data with shops information
    order_data = OrderReadNested.model_validate(order)

    # Get unique shops from order products
    shops = set()
    for order_product in order.order_products:
        if order_product.shop_id:
            shops.add(order_product.shop_id)

    # Get shop details
    shop_details = []
    for shop_id in shops:
        shop = session.get(Shop, shop_id)
        if shop:
            shop_details.append({"id": shop.id, "name": shop.name, "slug": shop.slug})

    order_data.shops = shop_details
    order_data.shop_count = len(shop_details)

    # Add fulfillment user info if fullfillment_id > 0
    order_data = add_fulfillment_user_info(order_data, order, session)

    return api_response(200, "Order Found", order_data)


@router.get("/tracking/{tracking_number}", response_model=OrderReadNested)
def get_by_tracking(tracking_number: str, session: GetSession):
    # order = session.exec(
    #     select(Order).where(Order.tracking_number == tracking_number)
    # ).first()
    # order = session.exec(
    # select(Order).where(Order.tracking_number == tracking_number)
    # ).one()
    order = session.scalar(
    select(Order).where(Order.tracking_number == tracking_number)
    )
    print(f"order:{order}")
    raiseExceptions((order, 404, "Order not found"))

    # Enhance order data with shops information
    order_data = OrderReadNested.model_validate(order)

    # Get unique shops from order products
    shops = set()
    for order_product in order.order_products:
        if order_product.shop_id:
            shops.add(order_product.shop_id)

    # Get shop details
    shop_details = []
    for shop_id in shops:
        shop = session.get(Shop, shop_id)
        if shop:
            shop_details.append({"id": shop.id, "name": shop.name, "slug": shop.slug})

    order_data.shops = shop_details
    order_data.shop_count = len(shop_details)

    # Add fulfillment user info if fullfillment_id > 0
    order_data = add_fulfillment_user_info(order_data, order, session)

    return api_response(200, "Order Found", order_data)


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


@router.get(
    "/list",
    response_model=list[OrderReadNested],
)
def list_orders(
    user: requireSignin,
    session: GetSession,
    dateRange: Optional[str] = None,
    numberRange: Optional[str] = None,
    searchTerm: str = None,
    columnFilters: Optional[str] = Query(None),
    order_status: Optional[OrderStatusEnum] = None,
    payment_status: Optional[PaymentStatusEnum] = None,
    shop_id: Optional[int] = None,  # ADDED: Filter by shop_id (from order products)
    sort: Optional[str] = Query(None, description="Sort by column. Example: ['created_at','desc'] or ['total','asc']"),
    page: int = None,
    skip: int = 0,
    limit: int = Query(200, ge=1, le=200),
):
    customFilters = [["customer_id", user.get("id")]]

    filters = {
        "searchTerm": searchTerm,
        "columnFilters": columnFilters,
        "dateRange": dateRange,
        "numberRange": numberRange,
        "customFilters": customFilters,
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

    # Handle shop filtering - we need to filter orders that have products from this shop
    if shop_id:
        # First get order IDs that have products from this shop
        order_ids_with_shop = session.exec(
            select(OrderProduct.order_id)
            .where(OrderProduct.shop_id == shop_id)
            .distinct()
        ).all()

        if not order_ids_with_shop:
            return api_response(404, "No orders found for this shop")

        if "columnFilters" not in filters or not filters["columnFilters"]:
            filters["columnFilters"] = []
        filters["columnFilters"].append(
            ["id", [str(oid) for oid in order_ids_with_shop]]
        )

    result = listop(
        session=session,
        Model=Order,
        searchFields=searchFields,
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
        sort=sort,
    )

    if not result["data"]:
        return api_response(404, "No orders found")

    # Enhance each order with shop information and fulfillment user info
    enhanced_orders = []
    for order in result["data"]:
        order_data = OrderReadNested.model_validate(order)

        # Get unique shops from order products
        shops = set()
        for order_product in order.order_products:
            if order_product.shop_id:
                shops.add(order_product.shop_id)

        # Get shop details
        shop_details = []
        for s_id in shops:
            shop = session.get(Shop, s_id)
            if shop:
                shop_details.append(
                    {"id": shop.id, "name": shop.name, "slug": shop.slug}
                )

        order_data.shops = shop_details
        order_data.shop_count = len(shop_details)

        # Add fulfillment user info if fullfillment_id > 0
        order_data = add_fulfillment_user_info(order_data, order, session)

        enhanced_orders.append(order_data)

    return api_response(200, "Orders found", enhanced_orders, result["total"])


@router.get(
    "/listorder",
    response_model=list[OrderReadNested],
)
def list_all_orders(
    user: requireSignin,
    session: GetSession,
    dateRange: Optional[str] = None,
    numberRange: Optional[str] = None,
    searchTerm: str = None,
    columnFilters: Optional[str] = Query(None),
    order_status: Optional[OrderStatusEnum] = None,
    payment_status: Optional[PaymentStatusEnum] = None,
    shop_id: Optional[int] = None,  # ADDED: Filter by shop_id (from order products)
    sort: Optional[str] = Query(None, description="Sort by column. Example: ['created_at','desc'] or ['total','asc']"),
    page: int = None,
    skip: int = 0,
    limit: int = Query(200, ge=1, le=200),
):
   # customFilters = [["customer_id", user.get("id")]]
    print(f"user:{user}")
    filters = {
        "searchTerm": searchTerm,
        "columnFilters": columnFilters,
        "dateRange": dateRange,
        "numberRange": numberRange,
       # "customFilters": customFilters,
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

    # Handle shop filtering - we need to filter orders that have products from this shop
    if shop_id:
        # First get order IDs that have products from this shop
        order_ids_with_shop = session.exec(
            select(OrderProduct.order_id)
            .where(OrderProduct.shop_id == shop_id)
            .distinct()
        ).all()

        if not order_ids_with_shop:
            return api_response(404, "No orders found for this shop")

        if "columnFilters" not in filters or not filters["columnFilters"]:
            filters["columnFilters"] = []
        filters["columnFilters"].append(
            ["id", [str(oid) for oid in order_ids_with_shop]]
        )

    result = listop(
        session=session,
        Model=Order,
        searchFields=searchFields,
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
        sort=sort,
    )

    if not result["data"]:
        return api_response(404, "No orders found")

    # Enhance each order with shop information and fulfillment user info
    enhanced_orders = []
    for order in result["data"]:
        order_data = OrderReadNested.model_validate(order)

        # Get unique shops from order products
        shops = set()
        for order_product in order.order_products:
            if order_product.shop_id:
                shops.add(order_product.shop_id)

        # Get shop details
        shop_details = []
        for s_id in shops:
            shop = session.get(Shop, s_id)
            if shop:
                shop_details.append(
                    {"id": shop.id, "name": shop.name, "slug": shop.slug}
                )

        order_data.shops = shop_details
        order_data.shop_count = len(shop_details)

        # Add fulfillment user info if fullfillment_id > 0
        order_data = add_fulfillment_user_info(order_data, order, session)

        enhanced_orders.append(order_data)

    return api_response(200, "Orders found", enhanced_orders, result["total"])


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
    shop_id: Optional[int] = None,  # Now filters by shop in order products
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
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            query = query.where(Order.created_at <= end_dt)

        orders = session.exec(query).all()

        sales_data = {}
        total_revenue = 0
        total_products_sold = 0

        for order in orders:
            for order_product in order.order_products:
                # Apply shop filter if provided
                if shop_id and order_product.shop_id != shop_id:
                    continue

                # Apply product filter if provided
                if product_id and order_product.product_id != product_id:
                    continue

                product_id_val = order_product.product_id
                quantity = float(order_product.order_quantity)
                revenue = order_product.subtotal

                if product_id_val not in sales_data:
                    product = session.get(Product, product_id_val)
                    shop = (
                        session.get(Shop, order_product.shop_id)
                        if order_product.shop_id
                        else None
                    )
                    sales_data[product_id_val] = {
                        "product_id": product_id_val,
                        "product_name": product.name if product else "Unknown",
                        "product_sku": product.sku if product else "Unknown",
                        "shop_id": order_product.shop_id,
                        "shop_name": shop.name if shop else "Unknown",
                        "total_quantity_sold": 0,
                        "total_revenue": 0,
                        "average_price": 0,
                    }

                sales_data[product_id_val]["total_quantity_sold"] += quantity
                sales_data[product_id_val]["total_revenue"] += revenue
                total_products_sold += quantity
                total_revenue += revenue

        # Calculate average prices
        for product_data in sales_data.values():
            if product_data["total_quantity_sold"] > 0:
                product_data["average_price"] = (
                    product_data["total_revenue"] / product_data["total_quantity_sold"]
                )

        report = {
            "period": {"start_date": start_date, "end_date": end_date},
            "summary": {
                "total_orders": len(orders),
                "total_products_sold": total_products_sold,
                "total_revenue": total_revenue,
            },
            "product_sales": list(sales_data.values()),
        }

        return api_response(200, "Sales report generated", report)

    except Exception as e:
        return api_response(500, f"Error generating sales report: {str(e)}")


# Add this endpoint to check cancellation eligibility
# Enhanced version with admin-only cancellation for specific scenarios
@router.get("/{order_id}/cancellation-eligibility")
def check_cancellation_eligibility(
    order_id: int,
    session: GetSession,
    user: requireSignin = None  # Changed from isAuthenticated to requireSignin
):
    """Check if the current user can cancel this order"""
    Print(f"🔐 User : {user}")
    #user_data = user.get("user") if user else None
    
    #Print(f"🔐 User data: {user_data}")
    
    order = session.get(Order, order_id)
    if not order:
        return api_response(404, "Order not found")
    
    Print(f"📦 Order: {order.tracking_number}, Customer ID: {order.customer_id}, Status: {order.order_status}")
    
    eligibility = get_order_cancellation_eligibility(order, user)  # Pass user_data instead of user
    
    
    
    return api_response(
        200,
        "Cancellation eligibility checked",
        eligibility
    )

# Add this route to your orderRoute.py after the existing routes
@router.post("/{order_id}/cancel", response_model=OrderCancelResponse)
def cancel_order(
    order_id: int,
    session: GetSession,
    request: Optional[OrderCancelRequest] = None,    
    user: requireSignin = None
):
    """
    Cancel an order and return products to stock with proper authorization
    """
    
    # Extract user data from the nested structure
    user_data = user.get("user") if user else None
    user_id = user.get("id") if user else None
    is_admin = user.get("is_root", False) if user else False
    
    Print(f"🔐 User data: {user}")
    Print(f"🔐 User ID: {user_id}, Is Admin: {is_admin}")
    
    # Get the order using scalar() - simpler approach
    order = session.scalar(
        select(Order)
        .options(selectinload(Order.order_products))
        .where(Order.id == order_id)
    )
    
    if not order:
        return api_response(404, "Order not found")
    
    # Check if order is already cancelled
    if order.order_status == OrderStatusEnum.CANCELLED:
        return api_response(400, "Order is already cancelled")
    
    # Check if order can be cancelled (only pending/processing orders)
    non_cancellable_statuses = [
        OrderStatusEnum.COMPLETED,
        OrderStatusEnum.REFUNDED,
        OrderStatusEnum.FAILED
    ]
    
    if order.order_status in non_cancellable_statuses:
        return api_response(400, f"Cannot cancel order with status: {order.order_status}")
    
    # Authorization check
    is_guest_order = order.customer_id is None
    
    Print(f"🔐 Authorization check - User ID: {user_id}, Is Admin: {is_admin}, Guest Order: {is_guest_order}, Order Customer ID: {order.customer_id}")
    
    if is_guest_order:
        # Guest order - only admin can cancel
        if not user_data or not is_admin:
            return api_response(403, "Only admin can cancel guest orders")
        Print("✅ Admin cancelling guest order")
    else:
        # User order - only the order owner or admin can cancel
        if user_id != order.customer_id and not is_admin:
            return api_response(403, "You can only cancel your own orders")
        Print(f"✅ {'Admin' if is_admin else 'User'} cancelling {'their own' if user_id == order.customer_id else 'user'} order")
    
    try:
        # Start transaction
        Print(f"🔄 Starting cancellation process for order {order_id}")
        
        # 1. Restore inventory for all order products
        products_restocked = return_products_to_stock(session, order)
        
        # 2. Update order status
        order.order_status = OrderStatusEnum.CANCELLED
        order.payment_status = PaymentStatusEnum.REVERSAL
        
        # 3. Update cancelled amount if needed
        if order.paid_total and order.paid_total > 0:
            order.cancelled_amount = Decimal(str(order.paid_total))
        
        # 4. Update order status history
        update_order_status_history(session, order.id, "order_cancelled_date")
        
        # 5. Update shop earnings if order was completed (reverse earnings)
        reverse_shop_earnings(session, order)
        
        session.add(order)
        session.commit()
        session.refresh(order)
        
        Print(f"✅ Order {order_id} cancelled successfully")
        
        return OrderCancelResponse(
            message="Order cancelled successfully",
            order_id=order_id,
            status="cancelled",
            products_restocked=products_restocked,
            cancelled_at=datetime.now(),
            cancelled_by=user_id
        )
        
    except Exception as e:
        session.rollback()
        Print(f"❌ Error cancelling order {order_id}: {str(e)}")
        import traceback
        Print(f"📋 Traceback: {traceback.format_exc()}")
        return api_response(500, f"Failed to cancel order: {str(e)}")

        

def return_products_to_stock(session: GetSession, order: Order) -> bool:
    """Return all products in order back to stock"""
    Print(f"📦 Restoring inventory for {len(order.order_products)} products")
    
    products_restocked = False
    
    for order_product in order.order_products:
        try:
            quantity = float(order_product.order_quantity)
            Print(f"  🔄 Processing product {order_product.product_id}, quantity: {quantity}")
            
            if order_product.item_type == OrderItemType.SIMPLE:
                # Handle simple product
                product = session.get(Product, order_product.product_id)
                if product:
                    product.quantity += quantity
                    
                    # Update sales tracking
                    product.total_sold_quantity = max(0, product.total_sold_quantity - quantity)
                    
                    if product.quantity > 0:
                        product.in_stock = True
                    
                    session.add(product)
                    Print(f"    ✅ Restored {quantity} units to simple product {product.name}")
                    products_restocked = True
            
            elif order_product.item_type == OrderItemType.VARIABLE and order_product.variation_option_id:
                # Handle variable product
                variation = session.get(VariationOption, order_product.variation_option_id)
                if variation:
                    # Restore variation stock
                    variation.quantity += quantity
                    
                    # Update parent product quantity and sales tracking
                    product = session.get(Product, order_product.product_id)
                    if product:
                        product.total_sold_quantity = max(0, product.total_sold_quantity - quantity)
                        
                        # Recalculate total quantity from variations
                        total_variation_quantity = session.scalar(
                            select(func.sum(VariationOption.quantity)).where(
                                VariationOption.product_id == order_product.product_id
                            )
                        ) or 0
                        
                        product.quantity = total_variation_quantity
                        session.add(product)
                    
                    if variation.quantity > 0:
                        variation.is_active = True
                    
                    session.add(variation)
                    Print(f"    ✅ Restored {quantity} units to variation {variation.title}")
                    products_restocked = True
                    
        except (ValueError, TypeError) as e:
            Print(f"    ❌ Error processing product {order_product.product_id}: {str(e)}")
            continue
        except Exception as e:
            Print(f"    ❌ Unexpected error with product {order_product.product_id}: {str(e)}")
            continue
    
    return products_restocked

def reverse_shop_earnings(session: GetSession, order: Order):
    """Reverse shop earnings if order was completed before cancellation"""
    Print(f"💰 Reversing shop earnings for order {order.id}")
    
    # Find and delete shop earnings for this order
    shop_earnings = session.exec(
        select(ShopEarning).where(ShopEarning.order_id == order.id)
    ).all()
    
    for earning in shop_earnings:
        session.delete(earning)
        Print(f"    ✅ Reversed shop earning for shop {earning.shop_id}")
    
    return len(shop_earnings) > 0



# Update the admin cancel route (already using requirePermission which should be fine)
@router.get("/{order_id}/cancellation-eligibility")
def check_cancellation_eligibility(
    order_id: int,
    session: GetSession,
    user: requireSignin = None
):
    """Check if the current user can cancel this order"""
    
    # Extract user data from the nested structure
    user_data = user.get("user") if user else None
    
    Print(f"🔐 User data: {user_data}")
    
    order = session.get(Order, order_id)
    if not order:
        return api_response(404, "Order not found")
    
    Print(f"📦 Order: {order.tracking_number}, Customer ID: {order.customer_id}, Status: {order.order_status}")
    
    eligibility = get_order_cancellation_eligibility(order, user_data)  # Pass user_data instead of user
    
    return api_response(
        200,
        "Cancellation eligibility checked",
        eligibility
    )

@router.post("/{order_id}/admin-cancel", response_model=OrderCancelResponse)
def admin_cancel_order(
    order_id: int,
    request: OrderCancelRequest,
    session: GetSession,
    user = requirePermission("order-cancel")
):
    """
    Admin-only cancellation with additional controls
    """
    
    # Extract user data from the nested structure
    user_data = user.get("user") if user else None
    user_id = user_data.get("id") if user_data else None
    is_admin = user_data.get("is_root", False) if user_data else False
    
    Print(f"🔐 Admin user data: {user_data}")
    
    # Get the order
    order = session.scalar(
        select(Order)
        .options(selectinload(Order.order_products))
        .where(Order.id == order_id)
    )
    
    if not order:
        return api_response(404, "Order not found")
    
    if order.order_status == OrderStatusEnum.CANCELLED:
        return api_response(400, "Order is already cancelled")
    
    Print(f"🔐 Admin cancellation by user {user_id} for order {order_id}")
    Print(f"📝 Cancellation reason: {request.reason}")
    
    try:
        # Restore inventory
        products_restocked = return_products_to_stock(session, order)
        
        # Update order status
        order.order_status = OrderStatusEnum.CANCELLED
        order.payment_status = PaymentStatusEnum.REVERSAL
        
        # Store cancellation reason
        if request.reason:
            Print(f"💾 Storing cancellation reason: {request.reason}")
        
        # Update order status history
        update_order_status_history(session, order.id, "order_cancelled_date")
        
        # Reverse shop earnings
        reverse_shop_earnings(session, order)
        
        session.add(order)
        session.commit()
        
        return OrderCancelResponse(
            message=f"Order cancelled by admin. Reason: {request.reason or 'Not specified'}",
            order_id=order_id,
            status="cancelled",
            products_restocked=products_restocked,
            cancelled_at=datetime.now(),
            cancelled_by=user_id
        )
        
    except Exception as e:
        session.rollback()
        Print(f"❌ Admin cancellation failed: {str(e)}")
        return api_response(500, f"Admin cancellation failed: {str(e)}")       


def get_order_cancellation_eligibility(order: Order, user_data: Optional[Dict]) -> Dict[str, Any]:
    """
    Check if order can be cancelled by current user
    Returns eligibility information
    """
    print(f"user_data:{user_data}")
    is_guest_order = order.customer_id is None
    user_id = user_data.get("id") if user_data else None
    is_admin = user_data.get("is_root", False) if user_data else False
    
    Print(f"🔐 Eligibility check - User ID: {user_id}, Is Admin: {is_admin}, Order Customer ID: {order.customer_id}")
    
    # Basic eligibility
    can_cancel = False
    reason = ""
    
    if order.order_status == OrderStatusEnum.CANCELLED:
        reason = "Order is already cancelled"
    elif order.order_status in [OrderStatusEnum.COMPLETED, OrderStatusEnum.REFUNDED]:
        reason = f"Cannot cancel order with status: {order.order_status}"
    elif is_guest_order:
        can_cancel = is_admin
        reason = "Guest orders can only be cancelled by admin" if not is_admin else "Admin can cancel guest orders"
    else:
        can_cancel = (user_id == order.customer_id) or is_admin
        reason = "You can only cancel your own orders" if not can_cancel else "Eligible for cancellation"
    
    return {
        "can_cancel": can_cancel,
        "reason": reason,
        "is_guest_order": is_guest_order,
        "requires_admin": is_guest_order,
        "current_user_is_owner": user_id == order.customer_id,
        "current_user_is_admin": is_admin,
        "order_status": order.order_status,
        "order_customer_id": order.customer_id,
        "current_user_id": user_id
    }

def create_shop_earning(session, order: Order):
    """Create shop earning records when order is completed - UPDATED for multi-shop orders"""
    if order.order_status != OrderStatusEnum.COMPLETED:
        return

    # Get all order products for this order
    order_products = session.exec(
        select(OrderProduct).where(OrderProduct.order_id == order.id)
    ).all()

    for order_product in order_products:
        if not order_product.shop_id:
            continue

        # Calculate shop earning for this specific product
        # (subtotal - admin_commission - proportional delivery fee)
        delivery_fee_per_product = Decimal("0.00")
        if order.delivery_fee and len(order_products) > 0:
            # Distribute delivery fee proportionally based on subtotal
            total_subtotal = sum(op.subtotal for op in order_products)
            if total_subtotal > 0:
                delivery_fee_per_product = Decimal(str(order.delivery_fee)) * (
                    Decimal(str(order_product.subtotal)) / Decimal(str(total_subtotal))
                )

        shop_earning = (
            Decimal(str(order_product.subtotal))
            - order_product.admin_commission
            - delivery_fee_per_product
        )

        # Create shop earning record for this shop and product
        earning = ShopEarning(
            shop_id=order_product.shop_id,
            order_id=order.id,
            order_product_id=order_product.id,  # Link to specific order product
            order_amount=Decimal(str(order_product.subtotal)),
            admin_commission=order_product.admin_commission,
            shop_earning=shop_earning,
        )

        session.add(earning)


# ==========================================
# NEW: Role-based Order Statistics & Lists
# ==========================================

@router.get("/my-statistics")
def get_my_order_statistics(
    user: requireSignin,
    session: GetSession,
):
    """
    Get order statistics based on user role:
    - fulfillment role: Count orders assigned to user (fullfillment_id)
    - shop_admin role: Count orders from user's shops (includes cancelled/returned)
    - root role: Count all orders (includes cancelled/returned)
    """
    user_id = user.get("id")
    role_names = user.get("roles", [])
    print(f"role_names:{role_names}")
    # Determine role priority: root > shop_admin > fulfillment
    is_root = user.get("is_root", False) or "root" in role_names
    is_shop_admin = "shop_admin" in role_names
    is_fulfillment = "fulfillment" in role_names or "Fulfillment" in role_names

    # Build base query
    completed_query = select(func.count(Order.id)).where(
        Order.order_status == OrderStatusEnum.COMPLETED
    )
    not_completed_query = select(func.count(Order.id)).where(
        Order.order_status != OrderStatusEnum.COMPLETED
    )

    # Additional counts for shop_admin and root
    cancelled_count = 0
    returned_count = 0

    if is_root:
        # Root: All orders, no filters
        pass
    elif is_shop_admin:
        # Get user's shops (use scalars to get list of IDs)
        user_shops = session.exec(
            select(Shop.id).where(Shop.owner_id == user_id)
        ).scalars().all()

        if not user_shops:
            return api_response(200, "No shops found for user", {
                "completed": 0,
                "not_completed": 0,
                "cancelled": 0,
                "returned": 0,
            })

        # Get order IDs that contain products from user's shops (use scalars)
        order_ids_with_shop = session.exec(
            select(OrderProduct.order_id)
            .where(OrderProduct.shop_id.in_(user_shops))
            .distinct()
        ).scalars().all()

        if not order_ids_with_shop:
            return api_response(200, "No orders found for user's shops", {
                "completed": 0,
                "not_completed": 0,
                "cancelled": 0,
                "returned": 0,
            })

        # Filter by shop orders
        completed_query = completed_query.where(Order.id.in_(order_ids_with_shop))
        not_completed_query = not_completed_query.where(Order.id.in_(order_ids_with_shop))

    elif is_fulfillment:
        # Fulfillment: Only orders assigned to this user
        completed_query = completed_query.where(Order.fullfillment_id == user_id)
        not_completed_query = not_completed_query.where(Order.fullfillment_id == user_id)
    else:
        return api_response(403, "User does not have required role for this endpoint")

    # Execute queries using scalar() to get the count value directly
    completed_count = session.exec(completed_query).scalar() or 0
    not_completed_count = session.exec(not_completed_query).scalar() or 0

    # Calculate cancelled and returned for shop_admin and root
    if is_root or is_shop_admin:
        cancelled_query = select(func.count(Order.id)).where(
            Order.order_status == OrderStatusEnum.CANCELLED
        )

        if is_shop_admin and order_ids_with_shop:
            cancelled_query = cancelled_query.where(Order.id.in_(order_ids_with_shop))

        cancelled_count = session.exec(cancelled_query).scalar() or 0

        # Count returned orders (order status = refunded)
        returned_query = select(func.count(Order.id)).where(
            Order.order_status == OrderStatusEnum.REFUNDED
        )

        if is_shop_admin and order_ids_with_shop:
            returned_query = returned_query.where(Order.id.in_(order_ids_with_shop))

        returned_count = session.exec(returned_query).scalar() or 0

    return api_response(200, "Order statistics retrieved", {
        "completed": completed_count,
        "not_completed": not_completed_count,
        "cancelled": cancelled_count,
        "returned": returned_count,
        "role": "root" if is_root else "shop_admin" if is_shop_admin else "fulfillment",
    })


@router.get("/my-completed", response_model=list[OrderReadNested])
def get_my_completed_orders(
    user: requireSignin,
    session: GetSession,
    limit: int = Query(20, ge=1, le=200, description="Number of orders to return (default: 20)"),
):
    """
    Get last N completed orders based on user role:
    - fulfillment role: Orders assigned to user (fullfillment_id)
    - shop_admin role: Orders from user's shops
    - root role: All completed orders
    """
    user_id = user.get("id")
    role_names = user.get("roles", [])

    # Determine role priority: root > shop_admin > fulfillment
    is_root = user.get("is_root", False) or "root" in role_names
    is_shop_admin = "shop_admin" in role_names
    is_fulfillment = "fulfillment" in role_names or "Fulfillment" in role_names

    # Build base query
    query = (
        select(Order)
        .where(Order.order_status == OrderStatusEnum.COMPLETED)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .options(
            selectinload(Order.order_products).selectinload(OrderProduct.product),
            selectinload(Order.order_status_history),
        )
    )

    if is_root:
        # Root: All completed orders
        pass
    elif is_shop_admin:
        # Get user's shops (use scalars to get list of IDs)
        user_shops = session.exec(
            select(Shop.id).where(Shop.owner_id == user_id)
        ).scalars().all()

        if not user_shops:
            return api_response(200, "No shops found for user", [], 0)

        # Get order IDs that contain products from user's shops (use scalars)
        order_ids_with_shop = session.exec(
            select(OrderProduct.order_id)
            .where(OrderProduct.shop_id.in_(user_shops))
            .distinct()
        ).scalars().all()

        if not order_ids_with_shop:
            return api_response(200, "No orders found for user's shops", [], 0)

        query = query.where(Order.id.in_(order_ids_with_shop))

    elif is_fulfillment:
        # Fulfillment: Only orders assigned to this user
        query = query.where(Order.fullfillment_id == user_id)
    else:
        return api_response(403, "User does not have required role for this endpoint")

    # Execute query and get scalar results (Order objects, not Row tuples)
    orders = session.exec(query).scalars().all()

    if not orders:
        return api_response(200, "No completed orders found", [], 0)

    # Enhance each order with shop information
    enhanced_orders = []
    for order in orders:
        order_data = OrderReadNested.model_validate(order)

        # Get unique shops from order products
        shops = set()
        for order_product in order.order_products:
            if order_product.shop_id:
                shops.add(order_product.shop_id)

        # Get shop details
        shop_details = []
        for s_id in shops:
            shop = session.get(Shop, s_id)
            if shop:
                shop_details.append(
                    {"id": shop.id, "name": shop.name, "slug": shop.slug}
                )

        order_data.shops = shop_details
        order_data.shop_count = len(shop_details)
        enhanced_orders.append(order_data)

    return api_response(200, "Completed orders retrieved", enhanced_orders, len(enhanced_orders))


@router.get("/my-not-completed", response_model=list[OrderReadNested])
def get_my_not_completed_orders(
    user: requireSignin,
    session: GetSession,
    limit: int = Query(20, ge=1, le=200, description="Number of orders to return (default: 20)"),
):
    """
    Get last N not-completed orders based on user role:
    - fulfillment role: Orders assigned to user (fullfillment_id)
    - shop_admin role: Orders from user's shops
    - root role: All not-completed orders
    """
    user_id = user.get("id")
    role_names = user.get("roles", [])

    # Determine role priority: root > shop_admin > fulfillment
    is_root = user.get("is_root", False) or "root" in role_names
    is_shop_admin = "shop_admin" in role_names
    is_fulfillment = "fulfillment" in role_names or "Fulfillment" in role_names

    # Build base query
    query = (
        select(Order)
        .where(Order.order_status != OrderStatusEnum.COMPLETED)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .options(
            selectinload(Order.order_products).selectinload(OrderProduct.product),
            selectinload(Order.order_status_history),
        )
    )

    if is_root:
        # Root: All not-completed orders
        pass
    elif is_shop_admin:
        # Get user's shops (use scalars to get list of IDs)
        user_shops = session.exec(
            select(Shop.id).where(Shop.owner_id == user_id)
        ).scalars().all()

        if not user_shops:
            return api_response(200, "No shops found for user", [], 0)

        # Get order IDs that contain products from user's shops (use scalars)
        order_ids_with_shop = session.exec(
            select(OrderProduct.order_id)
            .where(OrderProduct.shop_id.in_(user_shops))
            .distinct()
        ).scalars().all()

        if not order_ids_with_shop:
            return api_response(200, "No orders found for user's shops", [], 0)

        query = query.where(Order.id.in_(order_ids_with_shop))

    elif is_fulfillment:
        # Fulfillment: Only orders assigned to this user
        query = query.where(Order.fullfillment_id == user_id)
    else:
        return api_response(403, "User does not have required role for this endpoint")

    # Execute query and get scalar results (Order objects, not Row tuples)
    orders = session.exec(query).scalars().all()

    if not orders:
        return api_response(200, "No not-completed orders found", [], 0)

    # Enhance each order with shop information
    enhanced_orders = []
    for order in orders:
        order_data = OrderReadNested.model_validate(order)

        # Get unique shops from order products
        shops = set()
        for order_product in order.order_products:
            if order_product.shop_id:
                shops.add(order_product.shop_id)

        # Get shop details
        shop_details = []
        for s_id in shops:
            shop = session.get(Shop, s_id)
            if shop:
                shop_details.append(
                    {"id": shop.id, "name": shop.name, "slug": shop.slug}
                )

        order_data.shops = shop_details
        order_data.shop_count = len(shop_details)
        enhanced_orders.append(order_data)

    return api_response(200, "Not-completed orders retrieved", enhanced_orders, len(enhanced_orders))
