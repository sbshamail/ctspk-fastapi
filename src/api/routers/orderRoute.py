# src/api/routes/orderRoute.py
from datetime import datetime, timedelta
import ast
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import func, select,text,update as sql_update
from sqlmodel import SQLModel, Field, Relationship
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
    FulfillmentUserInfo,
    FreeShippingSource
)
from src.api.models.usersModel import User
from src.api.models.product_model.productsModel import Product, ProductRead, ProductType
from src.api.models.product_model.variationOptionModel import VariationOption
from src.api.models.category_model import Category
from src.api.models.shop_model.shopsModel import Shop
from src.api.models.shop_model.userShopModel import UserShop
from src.api.models.role_model.userRoleModel import UserRole
from src.api.models.withdrawModel import ShopEarning
# NEW: Import tax and shipping models
from src.api.models.taxModel import Tax
from src.api.models.shipping_model.shippingModel import Shipping
from src.api.models.couponModel import Coupon, CouponType
from src.api.models.addressModel import Address, AddressDetail, Location
from src.api.models.settingsModel import Settings
from src.api.models.returnModel import UserWallet, WalletTransaction
from src.api.core.dependencies import (
    GetSession,
    requirePermission,
    requireSignin,
    isAuthenticated,
)
from datetime import datetime
from src.api.core.utility import now_pk
import uuid
from decimal import Decimal
from src.api.core.transaction_logger import TransactionLogger
from src.api.core.notification_helper import NotificationHelper
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
    now = now_pk()
    return f"GTISB-{now:%Y-%m-%d}-{uuid.uuid4().hex[:8].upper()}"

def save_default_addresses_from_order(
    session,
    customer_id: Optional[int],
    billing_address: Optional[Dict[str, Any]],
    shipping_address: Optional[Dict[str, Any]],
    is_authenticated: bool = False
):
    """
    Save default billing and shipping addresses from order to user's address table.

    Logic:
    - Only process if user is authenticated (signed in)
    - Only process if customer_id exists (not a guest order)
    - Check if billing_address has is_default=true/1, save it and update other billing defaults to false
    - Check if shipping_address has is_default=true/1, save it and update other shipping defaults to false
    - Ensures only one default address per type (billing/shipping)

    Args:
        session: Database session
        customer_id: User ID (can be None for guest orders)
        billing_address: Billing address dict with optional is_default field
        shipping_address: Shipping address dict with optional is_default field
        is_authenticated: Whether user is authenticated/signed in
    """
    if not is_authenticated or not customer_id:
        # Guest order or not authenticated, skip address saving
        return

    # Process billing address
    if billing_address and billing_address.get('is_default') in [True, 1, '1', 'true', 'True']:
        # First, set all existing billing addresses for this user to is_default=False using UPDATE
        try:
            stmt = (
                sql_update(Address)
                .where(
                    Address.customer_id == customer_id,
                    Address.type == 'billing'
                )
                .values(is_default=False)
            )
            session.exec(stmt)
        except Exception as e:
            print(f"Error updating existing billing addresses: {e}")

        # Create new default billing address
        try:
            billing_detail = AddressDetail(
                street=billing_address.get('street', ''),
                city=billing_address.get('city', ''),
                state=billing_address.get('state'),
                postal_code=billing_address.get('postal_code'),
                country=billing_address.get('country')
            )

            location = None
            if billing_address.get('location'):
                location = Location(
                    lat=billing_address['location'].get('lat'),
                    lng=billing_address['location'].get('lng')
                )

            new_billing = Address(
                title=billing_address.get('title', 'Billing Address'),
                type='billing',
                is_default=True,
                address=billing_detail.model_dump(),  # Convert to dict for JSON serialization
                location=location.model_dump() if location else None,  # Convert to dict for JSON serialization
                customer_id=customer_id
            )
            session.add(new_billing)
        except Exception as e:
            print(f"Error saving billing address: {e}")

    # Process shipping address
    if shipping_address and shipping_address.get('is_default') in [True, 1, '1', 'true', 'True']:
        # First, set all existing shipping addresses for this user to is_default=False using UPDATE
        try:
            stmt = (
                sql_update(Address)
                .where(
                    Address.customer_id == customer_id,
                    Address.type == 'shipping'
                )
                .values(is_default=False)
            )
            session.exec(stmt)
        except Exception as e:
            print(f"Error updating existing shipping addresses: {e}")

        # Create new default shipping address
        try:
            shipping_detail = AddressDetail(
                street=shipping_address.get('street', ''),
                city=shipping_address.get('city', ''),
                state=shipping_address.get('state'),
                postal_code=shipping_address.get('postal_code'),
                country=shipping_address.get('country')
            )

            location = None
            if shipping_address.get('location'):
                location = Location(
                    lat=shipping_address['location'].get('lat'),
                    lng=shipping_address['location'].get('lng')
                )

            new_shipping = Address(
                title=shipping_address.get('title', 'Shipping Address'),
                type='shipping',
                is_default=True,
                address=shipping_detail.model_dump(),  # Convert to dict for JSON serialization
                location=location.model_dump() if location else None,  # Convert to dict for JSON serialization
                customer_id=customer_id
            )
            session.add(new_shipping)
        except Exception as e:
            print(f"Error saving shipping address: {e}")


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
    setattr(order_status, status_field, now_pk())
    session.add(order_status)


def validate_tax_shipping_coupon(
    session,
    tax_id: Optional[int],
    shipping_id: Optional[int],
    coupon_id: Optional[int],
    order_amount: float,
    language: str = "en"
) -> tuple[bool, str, Dict[str, Any]]:
    """
    Validate tax, shipping, and coupon with enhanced coupon validation
    and settings-based free shipping support.

    Returns: (is_valid, error_message, calculation_data)

    calculation_data includes:
    - tax_rate, tax_amount
    - shipping_amount (final amount after free shipping discount)
    - original_shipping_amount (original shipping before discount)
    - coupon_discount (discount amount from FIXED/PERCENTAGE coupons only)
    - coupon_type
    - free_shipping_source ('none', 'settings', 'coupon')
    """
    calculation_data = {
        'tax_rate': 0.0,
        'tax_amount': 0.0,
        'shipping_amount': 0.0,
        'original_shipping_amount': 0.0,
        'coupon_discount': 0.0,
        'coupon_type': None,
        'free_shipping_source': FreeShippingSource.NONE.value
    }

    # Validate tax
    if tax_id:
        tax = session.get(Tax, tax_id)
        if not tax:
            return False, "Tax not found", calculation_data
        if not tax.is_global and not tax.is_active:
            return False, "Tax is not active", calculation_data
        calculation_data['tax_rate'] = tax.rate

    # Validate shipping and store original amount
    original_shipping = 0.0
    if shipping_id:
        shipping = session.get(Shipping, shipping_id)
        if not shipping:
            return False, "Shipping not found", calculation_data
        if not shipping.is_active:
            return False, "Shipping is not active", calculation_data
        original_shipping = shipping.amount
        calculation_data['shipping_amount'] = original_shipping
        calculation_data['original_shipping_amount'] = original_shipping

    # Fetch settings for free shipping configuration
    settings_statement = select(Settings).where(Settings.language == language)
    settings_result = session.exec(settings_statement).first()

    # Handle Row object vs Settings model
    settings = None
    if settings_result:
        if hasattr(settings_result, 'options'):
            settings = settings_result
        elif hasattr(settings_result, '_mapping'):
            # Extract Settings from Row object
            mapping = dict(settings_result._mapping)
            settings = mapping.get('Settings') or mapping.get(Settings)

    # Fallback to English settings if language-specific not found
    if not settings and language != "en":
        settings_statement = select(Settings).where(Settings.language == "en")
        settings_result = session.exec(settings_statement).first()
        if settings_result:
            if hasattr(settings_result, 'options'):
                settings = settings_result
            elif hasattr(settings_result, '_mapping'):
                mapping = dict(settings_result._mapping)
                settings = mapping.get('Settings') or mapping.get(Settings)

    # Get free shipping settings (with defaults)
    free_shipping_enabled = False
    free_shipping_amount = 0       # order must reach this to qualify for free shipping
    minimum_order_amount = 0       # minimum order amount (always enforced)
    max_shipping_amount_off = 0    # max discount cap on shipping fee

    options = None
    if settings:
        if hasattr(settings, 'options'):
            options = settings.options
        elif isinstance(settings, dict):
            options = settings.get('options')

    def _to_float(val):
        try:
            return float(val or 0)
        except (ValueError, TypeError):
            return 0.0

    if options:
        free_shipping_enabled = bool(options.get('freeShipping', False))
        free_shipping_amount   = _to_float(options.get('freeShippingAmount', 0))
        minimum_order_amount   = _to_float(options.get('minimumOrderAmount', 0))
        max_shipping_amount_off = _to_float(options.get('maximumShippingAmountOff', 0))

    # Always enforce minimum order amount (independent of free shipping)
    if minimum_order_amount > 0 and order_amount < minimum_order_amount:
        return False, f"Minimum order amount is {minimum_order_amount} without shipping fee", calculation_data

    # Apply settings-based free shipping when enabled and order qualifies
    settings_free_shipping_applied = False
    if (
        free_shipping_enabled
        and original_shipping > 0
        and free_shipping_amount > 0
        and order_amount >= free_shipping_amount
    ):
        # Discount is capped by maximumShippingAmountOff (0 = no cap = full discount)
        shipping_discount = min(original_shipping, max_shipping_amount_off) if max_shipping_amount_off > 0 else original_shipping
        calculation_data['shipping_amount'] = original_shipping - shipping_discount
        calculation_data['free_shipping_source'] = FreeShippingSource.SETTINGS.value
        settings_free_shipping_applied = True

    # Validate coupon with enhanced checks
    if coupon_id:
        coupon = session.get(Coupon, coupon_id)
        if not coupon:
            return False, "Coupon not found", calculation_data

        # Check if coupon is active
        now = now_pk()
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
            # Only apply coupon free shipping if settings-based free shipping wasn't already applied
            if not settings_free_shipping_applied and original_shipping > 0:
                # Discount capped by maximumShippingAmountOff (0 = no cap = full discount)
                shipping_discount = min(original_shipping, max_shipping_amount_off) if max_shipping_amount_off > 0 else original_shipping
                calculation_data['shipping_amount'] = original_shipping - shipping_discount
                calculation_data['free_shipping_source'] = FreeShippingSource.COUPON.value
            # Note: coupon_discount stays 0.0 for FREE_SHIPPING coupons
            # The shipping discount is tracked via free_shipping_source field

    return True, "Validation successful", calculation_data


def calculate_product_discount(price: float, sale_price: Optional[float], quantity: float) -> float:
    """Calculate product-level discount"""
    if sale_price and sale_price > 0 and sale_price < price:
        return (price - sale_price) * quantity
    return 0.0


def calculate_item_tax(subtotal: float, tax_rate: float) -> float:
    """Calculate tax for individual item"""
    return subtotal * (tax_rate / 100)


def get_payment_status_by_gateway(payment_gateway: Optional[str]) -> str:
    """
    Determine payment status based on payment gateway.

    - payfast: payment-processing (awaiting IPN confirmation)
    - cod/cash_on_delivery: payment-cash-on-delivery
    - easypaisa/jazzcash: payment-success (instant confirmation)
    - wallet: payment-wallet
    - cash: payment-cash
    - Default: payment-pending
    """
    if not payment_gateway:
        return PaymentStatusEnum.PENDING.value

    gateway_lower = payment_gateway.lower().strip()

    if gateway_lower == "payfast":
        return PaymentStatusEnum.PROCESSING.value
    elif gateway_lower in ["cod", "cash_on_delivery", "cash-on-delivery", "cash on delivery"]:
        return PaymentStatusEnum.CASH_ON_DELIVERY.value
    elif gateway_lower in ["easypaisa", "jazzcash"]:
        return PaymentStatusEnum.SUCCESS.value
    elif gateway_lower == "wallet":
        return PaymentStatusEnum.WALLET.value
    elif gateway_lower == "cash":
        return PaymentStatusEnum.CASH.value
    else:
        return PaymentStatusEnum.PENDING.value


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

    # Get unique product IDs to handle duplicates in cart_items
    unique_product_ids = set(product_ids)

    # ✅ 2. Validate products exist in db
    products = (
        session.exec(select(Product).where(Product.id.in_(product_ids))).scalars().all()
    )
    if len(products) != len(unique_product_ids):
        found = {p.id for p in products}
        missing = [pid for pid in unique_product_ids if pid not in found]
        return api_response(404, f"Product(s) not found: {missing}")

    # ✅ 3. Fetch carts to clear after order creation (if user is authenticated)
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

    # ✅ 4. Calculate initial totals and validate variable products
    subtotal_amount = 0.0
    total_product_discount = 0.0
    actual_amount = 0.0  # Sum of (price * quantity) without any discount
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

        # Check if product is variable and requires variation_option_id
        if product.product_type == ProductType.VARIABLE:
            if not item.variation_option_id or item.variation_option_id <= 0:
                validation_errors.append(f"Product '{product.name}' is a variable product. Please select a valid variation option before purchasing.")
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

        # Calculate actual_amount (price * quantity without any discount)
        actual_amount += price * quantity

        # Use sale price if available, otherwise use regular price
        final_price = sale_price if sale_price and sale_price > 0 else price
        subtotal_amount += final_price * quantity

    if validation_errors:
        return api_response(400, "Product validation failed", {"errors": validation_errors})

    # NEW: Validate tax, shipping, and coupon (with settings-based free shipping)
    is_valid, error_msg, calc_data = validate_tax_shipping_coupon(
        session, request.tax_id, request.shipping_id, request.coupon_id, subtotal_amount, "en"
    )
    if not is_valid:
        return api_response(400, error_msg)

    # NEW: Calculate final amounts with tax, shipping, and coupon
    tax_amount = round(subtotal_amount * (calc_data['tax_rate'] / 100))
    shipping_amount = round(calc_data['shipping_amount'])
    original_shipping_amount = round(calc_data['original_shipping_amount'])
    coupon_discount = round(calc_data['coupon_discount'])
    free_shipping_source = calc_data['free_shipping_source']

    # Round subtotal and product discount
    subtotal_amount = round(subtotal_amount)
    total_product_discount = round(total_product_discount)

    # Calculate final total
    final_total = round(subtotal_amount + tax_amount + shipping_amount - coupon_discount)

    # Ensure total doesn't go below zero
    final_total = max(0, final_total)

    # ✅ WALLET DEDUCTION: Process wallet payment if requested
    wallet_amount_used = 0.0
    paid_total = final_total  # Amount to be paid after wallet deduction

    if user and request.use_wallet and final_total > 0:
        # Get user's wallet
        wallet = session.execute(
            select(UserWallet).where(UserWallet.user_id == user["id"])
        ).scalars().first()

        if wallet and wallet.balance > 0:
            # Calculate wallet amount to use
            if request.wallet_amount is not None and request.wallet_amount > 0:
                # Use specified amount (capped by balance and order total)
                wallet_amount_used = min(request.wallet_amount, wallet.balance, final_total)
            else:
                # Use max available (capped by order total)
                wallet_amount_used = min(wallet.balance, final_total)

            wallet_amount_used = round(wallet_amount_used, 2)

            if wallet_amount_used > 0:
                # Calculate remaining amount to pay
                paid_total = round(final_total - wallet_amount_used, 2)
                paid_total = max(0, paid_total)

    # ✅ 5. Build order fields with NEW fields
    tracking_number = generate_tracking_number()
    order = Order(
        tracking_number=tracking_number,
        customer_id=user["id"] if user else None,
        customer_contact=shipping_address.get("phone"),
        customer_name=shipping_address.get("name"),
        amount=subtotal_amount,  # Subtotal before discounts/taxes
        actual_amount=round(actual_amount),  # Sum of (price * quantity) without discount
        sales_tax=tax_amount,
        total=final_total,
        paid_total=paid_total,  # Amount to pay after wallet deduction
        discount=total_product_discount,  # Total product discounts
        coupon_discount=coupon_discount,  # NEW: Coupon discount
        wallet_amount_used=wallet_amount_used,  # NEW: Wallet amount used
        shipping_address=shipping_address,
        billing_address=shipping_address,  # same for now
        delivery_time=request.delivery_time,
        payment_gateway=request.payment_gateway,
        # NEW: Add tax_id, shipping_id, coupon_id
        tax_id=request.tax_id,
        shipping_id=request.shipping_id,
        coupon_id=request.coupon_id,
        delivery_fee=shipping_amount,
        original_delivery_fee=original_shipping_amount,  # NEW: Original shipping before free shipping
        free_shipping_source=free_shipping_source,  # NEW: Track source of free shipping
        order_status="order-pending",
        payment_status=get_payment_status_by_gateway(request.payment_gateway),
        language="en",
        payment_response=request.payment_response,  # Payment gateway response as JSON
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

        # Calculate item-level values (rounded to whole numbers)
        final_price = sale_price if sale_price and sale_price > 0 else price
        subtotal = round(final_price * quantity)
        item_discount = round(calculate_product_discount(price, sale_price, quantity))
        item_tax = round(calculate_item_tax(subtotal, calc_data['tax_rate']))

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
            unit_price=round(price),  # Original price
            sale_price=round(sale_price) if sale_price else None,  # NEW: Sale price
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
    order_status = OrderStatus(order_id=order.id, order_pending_date=now_pk())
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

    # Save default addresses to user's address table if is_default is set
    save_default_addresses_from_order(
        session=session,
        customer_id=user["id"] if user else None,
        billing_address=shipping_address,  # billing_address = shipping_address for cartcreate
        shipping_address=shipping_address,
        is_authenticated=user is not None
    )

    # ✅ 8. Create wallet transaction and update balance if wallet was used
    if wallet_amount_used > 0 and user:
        # Get the wallet again to ensure we have latest data
        wallet = session.execute(select(UserWallet).where(UserWallet.user_id == user["id"])).scalars().first()
        if wallet:
            # Calculate new balance
            new_balance = round(wallet.balance - wallet_amount_used, 2)

            # Create wallet transaction record
            wallet_transaction = WalletTransaction(
                user_id=user["id"],
                amount=wallet_amount_used,
                transaction_type="debit",
                balance_after=new_balance,
                description=f"Payment for order #{order.tracking_number}",
                is_refund=False,
                order_id=order.id
            )
            session.add(wallet_transaction)

            # Update wallet balance
            wallet.balance = new_balance
            wallet.total_debited = round(wallet.total_debited + wallet_amount_used, 2)
            session.add(wallet)

    try:
        session.commit()
        session.refresh(order)

        # Log order placement transaction
        try:
            logger = TransactionLogger(session)
            logger.log_order_placed(
                order=order,
                user_id=user["id"] if user else None,
                notes=f"Order {tracking_number} created from cart"
            )

            # Log stock deduction for each product
            for op in order_products:
                product = session.get(Product, op.product_id)
                if product:
                    logger.log_stock_deduction(
                        product=product,
                        quantity=int(float(op.order_quantity)),
                        user_id=user["id"] if user else None,
                        notes=f"Stock deducted for order {tracking_number}",
                        order_id=order.id,
                        order_product_id=op.id,
                        variation_option_id=op.variation_option_id if op.item_type == OrderItemType.VARIABLE else None,
                        unit_price=float(op.unit_price) if op.unit_price else None,
                        sale_price=float(op.sale_price) if op.sale_price else None,
                        subtotal=float(op.subtotal) if op.subtotal else None,
                        discount=float(op.item_discount) if op.item_discount else None,
                        tax=float(op.item_tax) if op.item_tax else None,
                        total=float(op.subtotal) if op.subtotal else None
                    )
        except Exception as e:
            Print(f"Failed to log order transaction: {e}")

        # Send notifications to customer, shop owners, and admins
        try:
            # Get unique shop IDs from order products
            shop_ids = list(set([op.shop_id for op in order_products if op.shop_id]))
            Print(f"📢 Sending notifications for order {tracking_number} to {len(shop_ids)} shop(s): {shop_ids}")

            if user:
                NotificationHelper.notify_order_placed(
                    session=session,
                    order_id=order.id,
                    tracking_number=tracking_number,
                    customer_id=user["id"],
                    shop_ids=shop_ids,
                    total_amount=float(final_total)
                )
                Print(f"✅ Notifications sent successfully")
        except Exception as e:
            Print(f"❌ Failed to send order notifications: {e}")
            import traceback
            Print(f"Traceback: {traceback.format_exc()}")

        # Send order confirmation email
        try:
            send_email(
                to_email=shipping_address.get("email") or order.customer_contact,
                email_template_id=5,  # Use appropriate template ID for order confirmation
                replacements={
                    "customer_name": order.customer_name,
                    "order_number": tracking_number,
                    "order_date":order.created_at,
                    "order_id": order.id,
                    "amount": order.amount,
                    "delivery_date":order.delivery_time,
                    "payment_gateway":order.payment_gateway,
                    "total_amount": f"Rs.{float(order.total):,.2f}" if order.total else "N/A",
                    "delivery_fee": f"Rs.{float(order.delivery_fee):,.2f}" if order.delivery_fee else "N/A" ,
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
    actual_amount = 0.0  # Sum of (price * quantity) without any discount
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

        # Check if product is variable and requires variation_option_id
        if product.product_type == ProductType.VARIABLE:
            if not variation_option_id or variation_option_id <= 0:
                error_msg = f"Product '{product.name}' is a variable product. Please select a valid variation option before purchasing."
                Print(f"   ❌ {error_msg}")
                validation_errors.append(error_msg)
                continue

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

        # Calculate actual_amount (price * quantity without any discount)
        actual_amount += price * quantity

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

    # ✅ 6. Validate tax, shipping, and coupon (with settings-based free shipping)
    is_valid, error_msg, calc_data = validate_tax_shipping_coupon(
        session, request.tax_id, request.shipping_id, request.coupon_id, subtotal_amount, "en"
    )
    if not is_valid:
        return api_response(400, error_msg)

    # ✅ 7. Calculate final amounts with tax, shipping, and coupon (rounded to whole numbers)
    tax_amount = round(subtotal_amount * (calc_data['tax_rate'] / 100))
    shipping_amount = round(calc_data['shipping_amount'])
    original_shipping_amount = round(calc_data['original_shipping_amount'])
    coupon_discount = round(calc_data['coupon_discount'])
    free_shipping_source = calc_data['free_shipping_source']

    # Round subtotal and product discount
    subtotal_amount = round(subtotal_amount)
    total_product_discount = round(total_product_discount)

    # Calculate final total
    final_total = round(subtotal_amount + tax_amount + shipping_amount - coupon_discount)

    # Ensure total doesn't go below zero
    final_total = max(0, final_total)

    # ✅ 7.5. Calculate wallet deduction if requested
    wallet_amount_used = 0.0
    paid_total = final_total

    if request.use_wallet and final_total > 0:
        # Get user's wallet
        wallet = session.execute(select(UserWallet).where(UserWallet.user_id == user_id)).scalars().first()
        if wallet and wallet.balance > 0:
            # Determine amount to use from wallet
            if request.wallet_amount is not None and request.wallet_amount > 0:
                # Use specified amount (capped by balance and total)
                wallet_amount_used = min(request.wallet_amount, wallet.balance, final_total)
            else:
                # Use entire wallet balance (capped by total)
                wallet_amount_used = min(wallet.balance, final_total)

            wallet_amount_used = round(wallet_amount_used, 2)

            if wallet_amount_used > 0:
                # Calculate remaining amount to pay
                paid_total = round(final_total - wallet_amount_used, 2)
                paid_total = max(0, paid_total)

    # ✅ 8. Create order with enhanced fields
    tracking_number = generate_tracking_number()

    order = Order(
        tracking_number=tracking_number,
        customer_id=user_id,
        customer_contact=shipping_address.get("phone"),
        customer_name=shipping_address.get("name"),
        amount=subtotal_amount,  # Subtotal before discounts/taxes
        actual_amount=round(actual_amount),  # Sum of (price * quantity) without discount
        sales_tax=tax_amount,
        total=final_total,
        paid_total=paid_total,  # Amount to pay after wallet deduction
        wallet_amount_used=wallet_amount_used,  # NEW: Wallet amount used
        discount=total_product_discount,  # Total product discounts
        coupon_discount=coupon_discount,  # Coupon discount
        shipping_address=shipping_address,
        billing_address=shipping_address,  # Same as shipping for now
        # Add tax_id, shipping_id, coupon_id
        delivery_time=request.delivery_time,
        payment_gateway=request.payment_gateway,
        tax_id=request.tax_id,
        shipping_id=request.shipping_id,
        coupon_id=request.coupon_id,
        delivery_fee=shipping_amount,
        original_delivery_fee=original_shipping_amount,  # NEW: Original shipping before free shipping
        free_shipping_source=free_shipping_source,  # NEW: Track source of free shipping
        order_status=OrderStatusEnum.PENDING.value,
        payment_status=get_payment_status_by_gateway(request.payment_gateway),
        language="en",
        payment_response=request.payment_response,  # Payment gateway response (null for COD)
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

        # Calculate item-level values (rounded to whole numbers)
        quantity = float(product_data.order_quantity)
        item_discount = round(calculate_product_discount(
            product_data.unit_price,
            product.sale_price if product.sale_price and product.sale_price > 0 else None,
            quantity
        ))
        item_tax = round(calculate_item_tax(product_data.subtotal, calc_data['tax_rate']))

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
            unit_price=round(product_data.unit_price),
            sale_price=round(product.sale_price) if product.sale_price and product.sale_price > 0 else None,
            subtotal=round(product_data.subtotal),
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
    order_status = OrderStatus(order_id=order.id, order_pending_date=now_pk())
    session.add(order_status)
    
    # ✅ 12. CLEAR USER'S CART after successful order creation
    try:
        # Delete all cart items for this user
        delete_stmt = select(Cart).where(Cart.user_id == user_id)
        cart_items_to_delete = session.execute(delete_stmt).scalars().all()

        # Delete all cart items
        for cart_item in cart_items_to_delete:
            session.delete(cart_item)

        # Save default addresses to user's address table if is_default is set
        save_default_addresses_from_order(
            session=session,
            customer_id=user_id,
            billing_address=request.billing_address,
            shipping_address=request.shipping_address,
            is_authenticated=True  # This endpoint requires authentication (requireSignin)
        )

        # ✅ Create wallet transaction and update balance if wallet was used
        if wallet_amount_used > 0:
            # Get the wallet again to ensure we have latest data
            wallet = session.execute(select(UserWallet).where(UserWallet.user_id == user_id)).scalars().first()
            if wallet:
                # Calculate new balance
                new_balance = round(wallet.balance - wallet_amount_used, 2)

                # Create wallet transaction record
                wallet_transaction = WalletTransaction(
                    user_id=user_id,
                    amount=wallet_amount_used,
                    transaction_type="debit",
                    balance_after=new_balance,
                    description=f"Payment for order #{order.tracking_number}",
                    is_refund=False,
                    order_id=order.id
                )
                session.add(wallet_transaction)

                # Update wallet balance
                wallet.balance = new_balance
                wallet.total_debited = round(wallet.total_debited + wallet_amount_used, 2)
                session.add(wallet)

        # Commit all changes (order creation + cart clearance + wallet transaction)
        session.commit()

        Print(f"✅ Successfully cleared {len(cart_items_to_delete)} items from cart")

        # Log order placement transaction
        try:
            logger = TransactionLogger(session)
            logger.log_order_placed(
                order=order,
                user_id=user_id,
                notes=f"Order {tracking_number} created from user cart"
            )

            # Log stock deduction for each product
            for op in created_order_products:
                product = session.get(Product, op.product_id)
                if product:
                    logger.log_stock_deduction(
                        product=product,
                        quantity=int(float(op.order_quantity)),
                        user_id=user_id,
                        notes=f"Stock deducted for order {tracking_number}",
                        order_id=order.id,
                        order_product_id=op.id,
                        variation_option_id=op.variation_option_id if op.item_type == OrderItemType.VARIABLE else None,
                        unit_price=float(op.unit_price) if op.unit_price else None,
                        sale_price=float(op.sale_price) if op.sale_price else None,
                        subtotal=float(op.subtotal) if op.subtotal else None,
                        discount=float(op.item_discount) if op.item_discount else None,
                        tax=float(op.item_tax) if op.item_tax else None,
                        total=float(op.subtotal) if op.subtotal else None
                    )
        except Exception as e:
            Print(f"❌ Failed to log order transaction: {e}")

        # Send notifications to customer, shop owners, and admins
        try:
            # Get unique shop IDs from created order products
            shop_ids = list(set([op.shop_id for op in created_order_products if op.shop_id]))
            Print(f"📢 Sending notifications for order {tracking_number} to {len(shop_ids)} shop(s): {shop_ids}")

            NotificationHelper.notify_order_placed(
                session=session,
                order_id=order.id,
                tracking_number=tracking_number,
                customer_id=user_id,
                shop_ids=shop_ids,
                total_amount=float(final_total)
            )
            Print(f"✅ Notifications sent successfully")
        except Exception as e:
            Print(f"❌ Failed to send order notifications: {e}")
            import traceback
            Print(f"Traceback: {traceback.format_exc()}")

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
                "order_number": tracking_number,
                "order_date":order.created_at,
                "order_id": order.id,
                "amount": f"Rs.{float(order.amount):,.2f}" if order.amount else "N/A",
                "delivery_date":order.delivery_time,
                "payment_gateway":order.payment_gateway,
                "total_amount": f"Rs.{float(order.total):,.2f}" if order.total else "N/A",
                "delivery_fee": f"Rs.{float(order.delivery_fee):,.2f}" if order.delivery_fee else "N/A",
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
    actual_amount = 0.0  # Sum of (price * quantity) without any discount
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

        # Check if product is variable and requires variation_option_id
        if product.product_type == ProductType.VARIABLE:
            variation_id = getattr(op_request, 'variation_option_id', None)
            if not variation_id or variation_id <= 0:
                validation_errors.append(f"Product '{product.name}' is a variable product. Please select a valid variation option before purchasing.")
                continue
            # Verify variation belongs to product
            variation = session.get(VariationOption, variation_id)
            if not variation or variation.product_id != product.id:
                validation_errors.append(f"Invalid variation option for product '{product.name}'. Please select a valid option.")
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

        # Calculate actual_amount (price * quantity without any discount)
        actual_amount += op_request.unit_price * quantity

        subtotal_amount += op_request.subtotal

    if validation_errors:
        return api_response(400, "Product validation failed", {"errors": validation_errors})

    # NEW: Validate tax, shipping, and coupon (with settings-based free shipping)
    is_valid, error_msg, calc_data = validate_tax_shipping_coupon(
        session, request.tax_id, request.shipping_id, request.coupon_id, subtotal_amount, "en"
    )
    if not is_valid:
        return api_response(400, error_msg)

    # NEW: Calculate final amounts with tax, shipping, and coupon (rounded to whole numbers)
    tax_amount = round(subtotal_amount * (calc_data['tax_rate'] / 100))
    shipping_amount = round(calc_data['shipping_amount'])
    original_shipping_amount = round(calc_data['original_shipping_amount'])
    coupon_discount = round(calc_data['coupon_discount'])
    free_shipping_source = calc_data['free_shipping_source']

    # Round subtotal and product discount
    subtotal_amount = round(subtotal_amount)
    total_product_discount = round(total_product_discount)

    # Calculate final total
    final_total = round(subtotal_amount + tax_amount + shipping_amount - coupon_discount)

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
        actual_amount=round(actual_amount),  # Sum of (price * quantity) without discount
        sales_tax=tax_amount,
        total=final_total,
        paid_total=final_total,  # Set paid_total = total
        discount=total_product_discount,
        coupon_discount=coupon_discount,  # NEW: Coupon discount
        payment_gateway=request.payment_gateway,
        shipping_address=request.shipping_address,
        billing_address=request.billing_address,
        logistics_provider=request.logistics_provider,
        delivery_fee=shipping_amount,
        original_delivery_fee=original_shipping_amount,  # NEW: Original shipping before free shipping
        free_shipping_source=free_shipping_source,  # NEW: Track source of free shipping
        delivery_time=request.delivery_time,
        # NEW: Add tax_id, shipping_id, coupon_id
        tax_id=request.tax_id,
        shipping_id=request.shipping_id,
        coupon_id=request.coupon_id,
        order_status="order-pending",
        payment_status=get_payment_status_by_gateway(request.payment_gateway),
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

        # Calculate item-level values (rounded to whole numbers)
        item_discount = round(calculate_product_discount(
            op_request.unit_price,
            product.sale_price if product.sale_price and product.sale_price > 0 else None,
            quantity
        ))
        item_tax = round(calculate_item_tax(op_request.subtotal, calc_data['tax_rate']))

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
            unit_price=round(op_request.unit_price),
            sale_price=round(product.sale_price) if product.sale_price and product.sale_price > 0 else None,
            subtotal=round(op_request.subtotal),
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
    order_status = OrderStatus(order_id=order.id, order_pending_date=now_pk())
    session.add(order_status)

    # Save default addresses to user's address table if is_default is set
    customer_id = request.customer_id or (user["id"] if user else None)
    save_default_addresses_from_order(
        session=session,
        customer_id=customer_id,
        billing_address=request.billing_address,
        shipping_address=request.shipping_address,
        is_authenticated=user is not None
    )

    try:
        session.commit()

        # Log order placement transaction
        logger = TransactionLogger(session)
        logger.log_order_placed(
            order=order,
            user_id=request.customer_id or (user["id"] if user else None),
            notes=f"Order {tracking_number} created"
        )

        # Log stock deduction for each product
        for op in order_products:
            product = session.get(Product, op.product_id)
            if product:
                logger.log_stock_deduction(
                    product=product,
                    quantity=int(float(op.order_quantity)),
                    user_id=request.customer_id or (user["id"] if user else None),
                    notes=f"Stock deducted for order {tracking_number}",
                    order_id=order.id,
                    order_product_id=op.id,
                    variation_option_id=op.variation_option_id if op.item_type == OrderItemType.VARIABLE else None,
                    unit_price=float(op.unit_price) if op.unit_price else None,
                    sale_price=float(op.sale_price) if op.sale_price else None,
                    subtotal=float(op.subtotal) if op.subtotal else None,
                    discount=float(op.item_discount) if op.item_discount else None,
                    tax=float(op.item_tax) if op.item_tax else None,
                    total=float(op.subtotal) if op.subtotal else None
                )

        # Send notifications to shop owners and admins (always), and customer (if logged in)
        customer_id = request.customer_id or (user["id"] if user else None)
        # Get unique shop IDs from order products
        shop_ids = list(set([op.shop_id for op in order_products if op.shop_id]))

        NotificationHelper.notify_order_placed(
            session=session,
            order_id=order.id,
            tracking_number=tracking_number,
            customer_id=customer_id,  # Can be None for guest users
            shop_ids=shop_ids,
            total_amount=float(final_total)
        )

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

    # Track changes before update
    old_order_status = order.order_status
    old_fulfillment_id = order.fullfillment_id

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
            OrderStatusEnum.ORDER_DELIVER: "order_deliver_date",
        }

        status_field = status_field_map.get(request.order_status)
        if status_field:
            update_order_status_history(session, order.id, status_field)

    session.commit()
    session.refresh(order)

    # Create shop earnings if order is completed
    create_shop_earning(session, order)
    session.commit()  # Commit shop earnings

    # Send fulfillment assignment notification + email when fullfillment_id is newly assigned
    new_fulfillment_id = request.fullfillment_id
    if new_fulfillment_id and new_fulfillment_id != old_fulfillment_id:
        try:
            fulfillment_user = session.get(User, new_fulfillment_id)
            if fulfillment_user:
                NotificationHelper.notify_order_assigned_to_fulfillment(
                    session=session,
                    order_id=order.id,
                    tracking_number=order.tracking_number,
                    customer_id=order.customer_id,
                    fulfillment_user_id=new_fulfillment_id
                )
                send_email(
                    to_email=fulfillment_user.email,
                    email_template_id=7,  # Fulfillment assignment template
                    replacements={
                        "fulfillment_name": fulfillment_user.name,
                        "order_number": order.tracking_number,
                        "order_id": order.id,
                        "customer_name": order.customer_name,
                        "order_total": f"Rs.{float(order.total):,.2f}" if order.total else "N/A",
                        "order_status": order.order_status.value if order.order_status else "N/A",
                    },
                    session=session
                )
        except Exception as e:
            Print(f"Failed to send fulfillment assignment notification/email: {e}")

    return api_response(
        200, "Order Updated Successfully", OrderReadNested.model_validate(order)
    )


@router.patch("/{id}/status")
def update_status(
    id: int, request: OrderStatusUpdate, session: GetSession, user: requireSignin
):
    order = session.get(Order, id)
    raiseExceptions((order, 404, "Order not found"))

    # ✅ ORDER STATUS SEQUENCE VALIDATION
    # Sequence: pending -> processing -> packed -> at_distribution_center -> at_local_facility -> out_for_delivery -> order_deliver -> completed
    ORDER_STATUS_SEQUENCE = [
        OrderStatusEnum.PENDING,              # 1
        OrderStatusEnum.PROCESSING,           # 2
        OrderStatusEnum.PACKED,               # 3
        OrderStatusEnum.AT_DISTRIBUTION_CENTER,  # 4
        OrderStatusEnum.AT_LOCAL_FACILITY,    # 5
        OrderStatusEnum.OUT_FOR_DELIVERY,     # 6
        OrderStatusEnum.ORDER_DELIVER,        # 7
        OrderStatusEnum.COMPLETED,            # 8
    ]

    # Special statuses that can be set at any time (not part of normal flow)
    SPECIAL_STATUSES = [
        OrderStatusEnum.CANCELLED,
        OrderStatusEnum.REFUNDED,
        OrderStatusEnum.FAILED,
    ]

    if request.order_status:
        current_status = order.order_status
        new_status = request.order_status

        # Convert string to enum if needed
        if isinstance(current_status, str):
            try:
                current_status = OrderStatusEnum(current_status)
            except ValueError:
                current_status = None

        # Allow special statuses (cancelled, refunded, failed) at any time
        if new_status not in SPECIAL_STATUSES:
            # Check if current status is a special status - cannot transition from special statuses
            if current_status in SPECIAL_STATUSES:
                return api_response(
                    400,
                    f"Cannot change status from '{current_status.value}' to '{new_status.value}'. Order is already {current_status.value.replace('order-', '')}.",
                    {
                        "current_status": current_status.value if current_status else None,
                        "requested_status": new_status.value,
                        "valid_sequence": [s.value for s in ORDER_STATUS_SEQUENCE]
                    }
                )

            # Get indices in sequence
            try:
                current_index = ORDER_STATUS_SEQUENCE.index(current_status) if current_status in ORDER_STATUS_SEQUENCE else -1
                new_index = ORDER_STATUS_SEQUENCE.index(new_status)
            except ValueError:
                return api_response(
                    400,
                    f"Invalid status transition",
                    {
                        "current_status": current_status.value if current_status else None,
                        "requested_status": new_status.value
                    }
                )

            # Validate sequence - new status must be exactly one step ahead
            if new_index != current_index + 1:
                if new_index <= current_index:
                    # Trying to go backwards or stay same
                    return api_response(
                        400,
                        f"Cannot change status from '{current_status.value}' to '{new_status.value}'. Status cannot go backwards.",
                        {
                            "current_status": current_status.value if current_status else None,
                            "current_step": current_index + 1,
                            "requested_status": new_status.value,
                            "requested_step": new_index + 1,
                            "next_valid_status": ORDER_STATUS_SEQUENCE[current_index + 1].value if current_index + 1 < len(ORDER_STATUS_SEQUENCE) else None,
                            "valid_sequence": [s.value for s in ORDER_STATUS_SEQUENCE]
                        }
                    )
                else:
                    # Trying to skip steps
                    expected_next = ORDER_STATUS_SEQUENCE[current_index + 1]
                    return api_response(
                        400,
                        f"Cannot skip status. Current: '{current_status.value}' -> Next must be: '{expected_next.value}', but got: '{new_status.value}'",
                        {
                            "current_status": current_status.value if current_status else None,
                            "current_step": current_index + 1,
                            "requested_status": new_status.value,
                            "requested_step": new_index + 1,
                            "next_valid_status": expected_next.value,
                            "skipped_statuses": [ORDER_STATUS_SEQUENCE[i].value for i in range(current_index + 1, new_index)],
                            "valid_sequence": [s.value for s in ORDER_STATUS_SEQUENCE]
                        }
                    )

    # Validate required images for specific statuses
    if request.order_status == OrderStatusEnum.OUT_FOR_DELIVERY:
        if not request.deliver_image:
            return api_response(
                400,
                "delivery_image is required when setting status to Out For Delivery",
                {"required_field": "deliver_image"}
            )
    if request.order_status == OrderStatusEnum.ORDER_DELIVER:
        if not request.completed_image:
            return api_response(
                400,
                "completed_image is required when setting status to Order Deliver",
                {"required_field": "completed_image"}
            )

    # Save deliver_image when status is OUT_FOR_DELIVERY
    if request.order_status == OrderStatusEnum.OUT_FOR_DELIVERY and request.deliver_image:
        order.deliver_image = request.deliver_image

    # Save completed_image when status is ORDER_DELIVER
    if request.order_status == OrderStatusEnum.ORDER_DELIVER and request.completed_image:
        order.completed_image = request.completed_image

    # Handle inventory restoration for cancelled/refunded orders
    if request.order_status in [
        OrderStatusEnum.CANCELLED,
        OrderStatusEnum.REFUNDED,
    ] and order.order_status not in [
        OrderStatusEnum.CANCELLED,
        OrderStatusEnum.REFUNDED,
    ]:

        # Restore inventory for all order products
        order_products = session.execute(
            select(OrderProduct).where(OrderProduct.order_id == id)
        ).scalars().all()

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
            OrderStatusEnum.ORDER_DELIVER: "order_deliver_date",
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

    # Create shop earnings if order is completed
    create_shop_earning(session, order)
    session.commit()  # Commit shop earnings

    # Send order status update email for OUT_FOR_DELIVERY and ORDER_DELIVER
    if request.order_status in [OrderStatusEnum.OUT_FOR_DELIVERY, OrderStatusEnum.ORDER_DELIVER]:
        try:
            customer_email = None
            if order.customer_id:
                customer = session.get(User, order.customer_id)
                if customer:
                    customer_email = customer.email

            if customer_email or order.customer_contact:
                send_email(
                    to_email=customer_email or order.customer_contact,
                    email_template_id=6,
                    replacements={
                        "customer_name": order.customer_name,
                        "tracking_number": order.tracking_number,
                        "order_number": order.tracking_number,
                        "order_id": order.id,
                        "order_status": order.order_status,
                        "payment_status": order.payment_status,
                    },
                    session=session
                )
        except Exception as e:
            Print(f"Failed to send order status update email: {e}")

    # Send cancellation/refund emails + notifications to customer, shop owners, and admin
    if request.order_status in [OrderStatusEnum.CANCELLED, OrderStatusEnum.REFUNDED]:
        try:
            shop_ids = list(set([op.shop_id for op in order.order_products if op.shop_id]))
            template_id = 8  # Order cancellation/refund template

            # Email customer
            customer_email = None
            if order.customer_id:
                customer = session.get(User, order.customer_id)
                if customer:
                    customer_email = customer.email
            if customer_email or order.customer_contact:
                send_email(
                    to_email=customer_email or order.customer_contact,
                    email_template_id=template_id,
                    replacements={
                        "customer_name": order.customer_name,
                        "order_number": order.tracking_number,
                        "order_id": order.id,
                        "order_status": order.order_status,
                    },
                    session=session
                )

            # Email shop owners
            for shop_id in shop_ids:
                shop = session.get(Shop, shop_id)
                if shop:
                    shop_owner = session.get(User, shop.owner_id)
                    if shop_owner:
                        send_email(
                            to_email=shop_owner.email,
                            email_template_id=template_id,
                            replacements={
                                "customer_name": order.customer_name,
                                "order_number": order.tracking_number,
                                "order_id": order.id,
                                "shop_name": shop.name,
                                "order_status": order.order_status,
                            },
                            session=session
                        )

            # Email + notify admins
            admin_users = session.exec(select(User).where(User.is_root == True)).all()
            for admin in admin_users:
                send_email(
                    to_email=admin.email,
                    email_template_id=template_id,
                    replacements={
                        "customer_name": order.customer_name,
                        "order_number": order.tracking_number,
                        "order_id": order.id,
                        "order_status": order.order_status,
                    },
                    session=session
                )

            # Notifications to customer, shops, admins
            if order.customer_id:
                NotificationHelper.notify_order_cancelled(
                    session=session,
                    order_id=order.id,
                    tracking_number=order.tracking_number,
                    customer_id=order.customer_id,
                    shop_ids=shop_ids,
                    cancelled_by="admin"
                )
        except Exception as e:
            Print(f"Failed to send cancellation/refund notifications: {e}")

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
            shop_details.append({
                "id": shop.id, 
                "name": shop.name, 
                "slug": shop.slug, 
                "is_active": shop.is_active
            })

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
    order_products = session.execute(
        select(OrderProduct).where(OrderProduct.order_id == id)
    ).scalars().all()

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
    order_status = session.execute(
        select(OrderStatus).where(OrderStatus.order_id == id)
    ).scalar_one_or_none()
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
    shop_s_active: Optional[bool] = Query(None, description="Filter by shop active status"),
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
    if shop_id or shop_s_active is not None:
        stmt = select(OrderProduct.order_id)
        if shop_id:
            stmt = stmt.where(OrderProduct.shop_id == shop_id)
        if shop_s_active is not None:
            stmt = stmt.join(Shop, OrderProduct.shop_id == Shop.id).where(Shop.is_active == shop_s_active)
            
        order_ids_with_shop = session.exec(stmt.distinct()).all()

        if not order_ids_with_shop:
            return api_response(404, "No orders found for this shop criteria")

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
        try:
            # Convert null values to empty strings or appropriate defaults
            if hasattr(order, 'customer_contact') and order.customer_contact is None:
                order.customer_contact = ""
            if hasattr(order, 'customer_name') and order.customer_name is None:
                order.customer_name = ""
            if hasattr(order, 'tracking_number') and order.tracking_number is None:
                order.tracking_number = ""  # Or generate one if business logic allows
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
        except Exception as e:
            # Log the problematic order but continue processing others
            Print(f"Error processing order {order.id if order else 'unknown'}: {str(e)}")
            continue  # Skip this order
    
    return api_response(200, "Orders found", enhanced_orders, result["total"])
@router.get(
    "/my-orders",
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
    shop_s_active: Optional[bool] = Query(None, description="Filter by shop active status"),
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
    if shop_id or shop_s_active is not None:
        stmt = select(OrderProduct.order_id)
        if shop_id:
            stmt = stmt.where(OrderProduct.shop_id == shop_id)
        if shop_s_active is not None:
            stmt = stmt.join(Shop, OrderProduct.shop_id == Shop.id).where(Shop.is_active == shop_s_active)
            
        order_ids_with_shop = session.exec(stmt.distinct()).all()

        if not order_ids_with_shop:
            return api_response(404, "No orders found for this shop criteria")

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
        try:
            # Convert null values to empty strings or appropriate defaults
            if hasattr(order, 'customer_contact') and order.customer_contact is None:
                order.customer_contact = ""
            if hasattr(order, 'customer_name') and order.customer_name is None:
                order.customer_name = ""
            if hasattr(order, 'tracking_number') and order.tracking_number is None:
                order.tracking_number = ""  # Or generate one if business logic allows
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
        except Exception as e:
            # Log the problematic order but continue processing others
            Print(f"Error processing order {order.id if order else 'unknown'}: {str(e)}")
            continue  # Skip this order
    
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
    shop_s_active: Optional[bool] = Query(None, description="Filter by shop active status"),
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
    if shop_id or shop_s_active is not None:
        stmt = select(OrderProduct.order_id)
        if shop_id:
            stmt = stmt.where(OrderProduct.shop_id == shop_id)
        if shop_s_active is not None:
            stmt = stmt.join(Shop, OrderProduct.shop_id == Shop.id).where(Shop.is_active == shop_s_active)
            
        order_ids_with_shop = session.exec(stmt.distinct()).all()

        if not order_ids_with_shop:
            return api_response(404, "No orders found for this shop criteria")

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
                    {
                        "id": shop.id, 
                        "name": shop.name, 
                        "slug": shop.slug, 
                        "is_active": shop.is_active
                    }
                )

        order_data.shops = shop_details
        order_data.shop_count = len(shop_details)

        # Add fulfillment user info if fullfillment_id > 0
        order_data = add_fulfillment_user_info(order_data, order, session)

        enhanced_orders.append(order_data)

    return api_response(200, "Orders found", enhanced_orders, result["total"])

@router.get(
    "/shoporders",
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
    shop_s_active: Optional[bool] = Query(None, description="Filter by shop active status"),
    sort: Optional[str] = Query(None, description="Sort by column. Example: ['created_at','desc'] or ['total','asc']"),
    page: int = None,
    skip: int = 0,
    limit: int = Query(200, ge=1, le=200),
):
    user_id = user.get("id")
    is_root = user.get("is_root", False)

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

    # Track order IDs to filter by (for non-root users or shop filtering)
    filter_order_ids = None

    # If user is NOT root, filter by user's shops
    if not is_root:
        # Get shops owned by the user
        user_shop_ids = session.execute(
            select(Shop.id).where(Shop.owner_id == user_id)
        ).scalars().all()

        if not user_shop_ids:
            return api_response(404, "No shops found for this user")

        # Get order IDs that have products from user's shops
        filter_order_ids = session.execute(
            select(OrderProduct.order_id)
            .where(OrderProduct.shop_id.in_(user_shop_ids))
            .distinct()
        ).scalars().all()

        if not filter_order_ids:
            return api_response(404, "No orders found for your shops")

    # Handle additional shop filtering if shop_id or shop_s_active is provided
    if shop_id or shop_s_active is not None:
        stmt = select(OrderProduct.order_id)
        if shop_id:
            stmt = stmt.where(OrderProduct.shop_id == shop_id)
        if shop_s_active is not None:
            stmt = stmt.join(Shop, OrderProduct.shop_id == Shop.id).where(Shop.is_active == shop_s_active)
            
        order_ids_with_shop = session.execute(stmt.distinct()).scalars().all()

        if not order_ids_with_shop:
            return api_response(404, "No orders found for this shop criteria")

        # Intersect with existing filter_order_ids if set
        if filter_order_ids is not None:
            filter_order_ids = list(set(filter_order_ids) & set(order_ids_with_shop))
        else:
            filter_order_ids = order_ids_with_shop

    # Build otherFilters function if we have order IDs to filter
    def order_id_filter(stmt, m):
        if filter_order_ids is not None:
            return stmt.where(m.id.in_(filter_order_ids))
        return stmt

    result = listop(
        session=session,
        Model=Order,
        searchFields=searchFields,
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
        sort=sort,
        otherFilters=order_id_filter if filter_order_ids else None,
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
                    {
                        "id": shop.id, 
                        "name": shop.name, 
                        "slug": shop.slug, 
                        "is_active": shop.is_active
                    }
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

@router.get("/sales-report")
def get_sales_report(
    session: GetSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    shop_id: Optional[int] = None,  # Now filters by shop in order products
    product_id: Optional[int] = None,
    user: requireSignin = None,
):
    """Get sales report with product-wise sales data"""
    try:
        # Get user info
        user_id = user.get("id")
        is_root = user.get("is_root", False)

        # Get user's shop IDs from user_shop table (for non-root users)
        user_shop_ids = []
        if not is_root:
            user_shop_results = session.exec(
                select(UserShop.shop_id).where(UserShop.user_id == user_id)
            ).all()
            user_shop_ids = [s if isinstance(s, int) else s[0] for s in user_shop_results]

            # If user has no shops assigned and is not root, deny access
            if not user_shop_ids:
                return api_response(403, "You don't have any shops assigned")

        # Validate shop_id access if specific shop requested
        if shop_id and not is_root:
            if shop_id not in user_shop_ids:
                return api_response(403, "You don't have access to this shop")

        # ===== COUNT 1: Total active shops (without any filters) =====
        total_active_shops_query = select(func.count(Shop.id)).where(Shop.is_active == True)
        
        # For non-root users, only count shops they have access to
        if not is_root and user_shop_ids:
            total_active_shops_query = total_active_shops_query.where(Shop.id.in_(user_shop_ids))
        
        total_active_shops = session.exec(total_active_shops_query).scalar() or 0

        # ===== COUNT 2: Shops with sales in the given interval =====
        # Build query to get order IDs for completed orders within date range
        order_query = select(Order.id).where(Order.order_status == OrderStatusEnum.COMPLETED)

        # Apply date filters for interval shops count
        interval_shop_date_conditions = []
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            interval_shop_date_conditions.append(Order.created_at >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            interval_shop_date_conditions.append(Order.created_at <= end_dt)

        for condition in interval_shop_date_conditions:
            order_query = order_query.where(condition)

        # Get order IDs for interval
        order_ids_result = session.exec(order_query).all()
        interval_order_ids = [row if isinstance(row, int) else row[0] for row in order_ids_result]

        # Count distinct shops that have sales in the interval
        shops_with_sales_query = select(func.count(OrderProduct.shop_id.distinct())).where(
            OrderProduct.order_id.in_(interval_order_ids) if interval_order_ids else False
        )
        
        # Apply user shop access filter
        if not is_root and user_shop_ids:
            shops_with_sales_query = shops_with_sales_query.where(
                OrderProduct.shop_id.in_(user_shop_ids)
            )
        
        shops_with_sales_in_interval = 0
        if interval_order_ids:  # Only execute if there are orders
            shops_with_sales_in_interval = session.exec(shops_with_sales_query).scalar() or 0

        # ===== COUNT 3: Distinct customers in the selected date period =====
        distinct_customers_query = select(func.count(Order.customer_id.distinct())).where(
            Order.order_status == OrderStatusEnum.COMPLETED
        )

        # Apply date filters
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            distinct_customers_query = distinct_customers_query.where(Order.created_at >= start_dt)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            distinct_customers_query = distinct_customers_query.where(Order.created_at <= end_dt)

        # Apply shop filter based on user access
        if shop_id:
            # If specific shop is selected, get orders from that shop
            shop_order_ids = session.exec(
                select(OrderProduct.order_id)
                .where(OrderProduct.shop_id == shop_id)
                .distinct()
            ).all()
            shop_order_ids = [row if isinstance(row, int) else row[0] for row in shop_order_ids]
            if shop_order_ids:
                distinct_customers_query = distinct_customers_query.where(Order.id.in_(shop_order_ids))
            else:
                distinct_customers_query = distinct_customers_query.where(False)
        elif not is_root and user_shop_ids:
            # Non-root users: only count customers from their shops
            shop_order_ids = session.exec(
                select(OrderProduct.order_id)
                .where(OrderProduct.shop_id.in_(user_shop_ids))
                .distinct()
            ).all()
            shop_order_ids = [row if isinstance(row, int) else row[0] for row in shop_order_ids]
            if shop_order_ids:
                distinct_customers_query = distinct_customers_query.where(Order.id.in_(shop_order_ids))
            else:
                distinct_customers_query = distinct_customers_query.where(False)

        # Execute customer count query
        distinct_customers = session.exec(distinct_customers_query).scalar() or 0

        # ===== MAIN REPORT DATA =====
        # Build query to get order IDs for completed orders (for main report)
        main_order_query = select(Order.id).where(Order.order_status == OrderStatusEnum.COMPLETED)

        # Apply date filters for main report
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            main_order_query = main_order_query.where(Order.created_at >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            main_order_query = main_order_query.where(Order.created_at <= end_dt)

        # Get order IDs for main report
        main_order_ids_result = session.exec(main_order_query).all()
        main_order_ids = [row if isinstance(row, int) else row[0] for row in main_order_ids_result]

        if not main_order_ids:
            return api_response(200, "Sales report generated", {
                "period": {"start_date": start_date, "end_date": end_date},
                "summary": {
                    "total_orders": 0,
                    "total_products_sold": 0,
                    "total_revenue": 0,
                    "total_active_shops": total_active_shops,
                    "shops_with_sales_in_interval": 0,
                    "distinct_customers": 0,
                },
                "product_sales": [],
            })

        # Query order products for main report
        op_query = select(OrderProduct).where(OrderProduct.order_id.in_(main_order_ids))

        # Apply shop filter based on user access
        if shop_id:
            # Specific shop requested (already validated above)
            op_query = op_query.where(OrderProduct.shop_id == shop_id)
        elif not is_root:
            # Non-root users: filter by their shops only
            op_query = op_query.where(OrderProduct.shop_id.in_(user_shop_ids))
        # Root users without shop_id filter see all shops

        # Apply product filter if provided
        if product_id:
            op_query = op_query.where(OrderProduct.product_id == product_id)

        order_products = session.exec(op_query).scalars().all()

        sales_data = {}
        total_revenue = 0
        total_products_sold = 0
        user_order_ids = set()  # Track unique orders containing user's shop products
        unique_shops_in_report = set()  # Track unique shops in the report data

        for order_product in order_products:
            prod_id = order_product.product_id
            quantity = float(order_product.order_quantity)
            revenue = order_product.subtotal

            # Track unique order IDs and shop IDs
            user_order_ids.add(order_product.order_id)
            if order_product.shop_id:
                unique_shops_in_report.add(order_product.shop_id)

            if prod_id not in sales_data:
                product = session.get(Product, prod_id)
                shop = (
                    session.get(Shop, order_product.shop_id)
                    if order_product.shop_id
                    else None
                )
                sales_data[prod_id] = {
                    "product_id": prod_id,
                    "product_name": product.name if product else "Unknown",
                    "product_sku": product.sku if product else "Unknown",
                    "shop_id": order_product.shop_id,
                    "shop_name": shop.name if shop else "Unknown",
                    "total_quantity_sold": 0,
                    "total_revenue": 0,
                    "average_price": 0,
                }

            sales_data[prod_id]["total_quantity_sold"] += quantity
            sales_data[prod_id]["total_revenue"] += revenue
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
                "total_orders": len(user_order_ids),
                "total_products_sold": total_products_sold,
                "total_revenue": total_revenue,
                "total_active_shops": total_active_shops,  # Total active shops (unfiltered)
                "shops_with_sales_in_interval": shops_with_sales_in_interval,  # Shops with sales in date range
                "shops_in_report_data": len(unique_shops_in_report),  # Shops that appear in the actual report data
                "distinct_customers": distinct_customers,  # Distinct customers in selected date period
            },
            "product_sales": list(sales_data.values()),
        }

        return api_response(200, "Sales report generated", report)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Sales report error: {error_details}")
        return api_response(500, f"Error generating sales report: {str(e)}")
# Product Sales Report
@router.get("/old-sales-report")
def get_sales_report(
    session: GetSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    shop_id: Optional[int] = None,  # Now filters by shop in order products
    product_id: Optional[int] = None,
    user: requireSignin = None,
):
    """Get sales report with product-wise sales data (filtered by user's shops)"""
    try:
        # Get user info
        user_id = user.get("id")
        is_root = user.get("is_root", False)

        # Get user's role IDs from database
        user_role_ids = session.exec(
            select(UserRole.role_id).where(UserRole.user_id == user_id)
        ).all()
        user_role_ids = [r if isinstance(r, int) else r[0] for r in user_role_ids]

        # Define role groups
        shop_restricted_roles = [21, 23, 24, 25]  # Roles that can only see their assigned shops
        all_shops_roles = [20, 22]  # Roles that can see all shops

        # Determine access level
        # 1. is_root=True -> see all shops
        # 2. Role IDs 21, 23, 24, 25 -> see only assigned shops
        # 3. Role IDs 20, 22 (and not in shop_restricted_roles) -> see all shops

        has_shop_restricted_role = any(role_id in shop_restricted_roles for role_id in user_role_ids)
        has_all_shops_role = any(role_id in all_shops_roles for role_id in user_role_ids)

        # Determine if user can see all shops
        can_see_all_shops = is_root or (has_all_shops_role and not has_shop_restricted_role)

        # Get user's shop IDs from user_shop table (for shop-restricted users)
        user_shop_ids = []
        if not can_see_all_shops:
            user_shop_results = session.exec(
                select(UserShop.shop_id).where(UserShop.user_id == user_id)
            ).all()
            user_shop_ids = [s if isinstance(s, int) else s[0] for s in user_shop_results]

            # If user has no shops assigned and can't see all shops, deny access
            if not user_shop_ids:
                return api_response(403, "You don't have any shops assigned")

        # Validate shop_id access if specific shop requested
        if shop_id and not can_see_all_shops:
            if shop_id not in user_shop_ids:
                return api_response(403, "You don't have access to this shop")

        # Build query to get order IDs for completed orders
        order_query = select(Order.id).where(Order.order_status == OrderStatusEnum.COMPLETED)

        # Apply date filters
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            order_query = order_query.where(Order.created_at >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            order_query = order_query.where(Order.created_at <= end_dt)

        # Get order IDs - need to extract scalar values
        order_ids_result = session.exec(order_query).all()

        # Extract actual ID values from result
        order_ids = [row if isinstance(row, int) else row[0] for row in order_ids_result]

        if not order_ids:
            return api_response(200, "Sales report generated", {
                "period": {"start_date": start_date, "end_date": end_date},
                "summary": {
                    "total_orders": 0,
                    "total_products_sold": 0,
                    "total_revenue": 0,
                },
                "product_sales": [],
            })

        # Query order products directly
        op_query = select(OrderProduct).where(OrderProduct.order_id.in_(order_ids))

        # Apply shop filter based on user access
        if shop_id:
            # Specific shop requested (already validated above)
            op_query = op_query.where(OrderProduct.shop_id == shop_id)
        elif not can_see_all_shops:
            # Shop-restricted users: filter by their assigned shops only
            op_query = op_query.where(OrderProduct.shop_id.in_(user_shop_ids))
        # Users who can see all shops without shop_id filter see all shops

        # Apply product filter if provided
        if product_id:
            op_query = op_query.where(OrderProduct.product_id == product_id)

        # Use scalars() to get proper OrderProduct instances
        order_products = session.exec(op_query).scalars().all()

        sales_data = {}
        total_revenue = 0
        total_products_sold = 0
        user_order_ids = set()  # Track unique orders containing user's shop products

        for order_product in order_products:
            prod_id = order_product.product_id
            quantity = float(order_product.order_quantity)
            revenue = order_product.subtotal

            # Track unique order IDs for user's shop products
            user_order_ids.add(order_product.order_id)

            if prod_id not in sales_data:
                product = session.get(Product, prod_id)
                shop = (
                    session.get(Shop, order_product.shop_id)
                    if order_product.shop_id
                    else None
                )
                sales_data[prod_id] = {
                    "product_id": prod_id,
                    "product_name": product.name if product else "Unknown",
                    "product_sku": product.sku if product else "Unknown",
                    "shop_id": order_product.shop_id,
                    "shop_name": shop.name if shop else "Unknown",
                    "total_quantity_sold": 0,
                    "total_revenue": 0,
                    "average_price": 0,
                }

            sales_data[prod_id]["total_quantity_sold"] += quantity
            sales_data[prod_id]["total_revenue"] += revenue
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
                "total_orders": len(user_order_ids),  # Only orders with user's shop products
                "total_products_sold": total_products_sold,
                "total_revenue": total_revenue,
            },
            "product_sales": list(sales_data.values()),
        }

        return api_response(200, "Sales report generated", report)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Sales report error: {error_details}")
        return api_response(500, f"Error generating sales report: {str(e)}")
@router.get("/shops-sales-report")
def get_shops_sales_report(
    session: GetSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    shop_id: Optional[int] = None,  # Now filters by shop in order products
    product_id: Optional[int] = None,
    user: requireSignin = None,
):
    """Get sales report with product-wise sales data (filtered by user's shops)"""
    try:
        # Get user's permissions and shops
        user_permissions = user.get("permissions", [])
        user_shops = user.get("shops", [])
        user_shop_ids = [shop["id"] for shop in user_shops]
        is_admin = "system:*" in user_permissions

        # Validate shop access
        if shop_id:
            if not is_admin and shop_id not in user_shop_ids:
                return api_response(403, "You don't have access to this shop")

        # If not admin and no specific shop_id, user must have at least one shop
        if not is_admin and not user_shop_ids:
            return api_response(403, "You don't have any shops assigned")

        # ===== COUNT 1: Total active shops (without any filters) =====
        total_active_shops_query = select(func.count(Shop.id)).where(Shop.is_active == True)
        
        # For non-admin users, only count shops they have access to
        if not is_admin and user_shop_ids:
            total_active_shops_query = total_active_shops_query.where(Shop.id.in_(user_shop_ids))
        
        total_active_shops = session.exec(total_active_shops_query).scalar() or 0

        # ===== COUNT 2: Shops with sales in the given interval =====
        # Build query to get order IDs for completed orders within date range
        order_query = select(Order.id).where(Order.order_status == OrderStatusEnum.COMPLETED)

        # Apply date filters for interval shops count
        interval_shop_date_conditions = []
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            interval_shop_date_conditions.append(Order.created_at >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            interval_shop_date_conditions.append(Order.created_at <= end_dt)

        for condition in interval_shop_date_conditions:
            order_query = order_query.where(condition)

        # Get order IDs for interval
        order_ids_result = session.exec(order_query).all()
        interval_order_ids = [row if isinstance(row, int) else row[0] for row in order_ids_result]

        # Count distinct shops that have sales in the interval
        shops_with_sales_query = select(func.count(OrderProduct.shop_id.distinct())).where(
            OrderProduct.order_id.in_(interval_order_ids) if interval_order_ids else False
        )
        
        # Apply user shop access filter
        if not is_admin and user_shop_ids:
            shops_with_sales_query = shops_with_sales_query.where(
                OrderProduct.shop_id.in_(user_shop_ids)
            )
        
        shops_with_sales_in_interval = 0
        if interval_order_ids:  # Only execute if there are orders
            shops_with_sales_in_interval = session.exec(shops_with_sales_query).scalar() or 0

        # ===== COUNT 3: Distinct customers in the selected date period =====
        distinct_customers_query = select(func.count(Order.customer_id.distinct())).where(
            Order.order_status == OrderStatusEnum.COMPLETED
        )

        # Apply date filters
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            distinct_customers_query = distinct_customers_query.where(Order.created_at >= start_dt)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            distinct_customers_query = distinct_customers_query.where(Order.created_at <= end_dt)

        # Apply shop filter based on user access
        if shop_id:
            # If specific shop is selected, get orders from that shop
            shop_order_ids = session.exec(
                select(OrderProduct.order_id)
                .where(OrderProduct.shop_id == shop_id)
                .distinct()
            ).all()
            shop_order_ids = [row if isinstance(row, int) else row[0] for row in shop_order_ids]
            if shop_order_ids:
                distinct_customers_query = distinct_customers_query.where(Order.id.in_(shop_order_ids))
            else:
                distinct_customers_query = distinct_customers_query.where(False)
        elif not is_admin and user_shop_ids:
            # Non-admin users: only count customers from their shops
            shop_order_ids = session.exec(
                select(OrderProduct.order_id)
                .where(OrderProduct.shop_id.in_(user_shop_ids))
                .distinct()
            ).all()
            shop_order_ids = [row if isinstance(row, int) else row[0] for row in shop_order_ids]
            if shop_order_ids:
                distinct_customers_query = distinct_customers_query.where(Order.id.in_(shop_order_ids))
            else:
                distinct_customers_query = distinct_customers_query.where(False)

        # Execute customer count query
        distinct_customers = session.exec(distinct_customers_query).scalar() or 0

        # ===== MAIN REPORT DATA =====
        # Build query to get order IDs for completed orders (for main report)
        main_order_query = select(Order.id).where(Order.order_status == OrderStatusEnum.COMPLETED)

        # Apply date filters for main report
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            main_order_query = main_order_query.where(Order.created_at >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            main_order_query = main_order_query.where(Order.created_at <= end_dt)

        # Get order IDs for main report
        main_order_ids_result = session.exec(main_order_query).all()
        main_order_ids = [row if isinstance(row, int) else row[0] for row in main_order_ids_result]

        if not main_order_ids:
            return api_response(200, "Sales report generated", {
                "period": {"start_date": start_date, "end_date": end_date},
                "summary": {
                    "total_orders": 0,
                    "total_products_sold": 0,
                    "total_revenue": 0,
                    "total_active_shops": total_active_shops,
                    "shops_with_sales_in_interval": 0,
                    "distinct_customers": 0,
                },
                "product_sales": [],
            })

        # Query order products directly
        op_query = select(OrderProduct).where(OrderProduct.order_id.in_(main_order_ids))

        # Apply shop filter based on user access
        if shop_id:
            # Specific shop requested (already validated above)
            op_query = op_query.where(OrderProduct.shop_id == shop_id)
        elif not is_admin:
            # Non-admin users: filter by their shops only
            op_query = op_query.where(OrderProduct.shop_id.in_(user_shop_ids))
        # Admin users without shop_id filter see all shops

        # Apply product filter if provided
        if product_id:
            op_query = op_query.where(OrderProduct.product_id == product_id)

        # Use scalars() to get proper OrderProduct instances
        order_products = session.exec(op_query).scalars().all()

        sales_data = {}
        total_revenue = 0
        total_products_sold = 0
        user_order_ids = set()  # Track unique orders containing user's shop products
        unique_shops_in_report = set()  # Track unique shops in the report data

        for order_product in order_products:
            prod_id = order_product.product_id
            quantity = float(order_product.order_quantity)
            revenue = order_product.subtotal

            # Track unique order IDs and shop IDs
            user_order_ids.add(order_product.order_id)
            if order_product.shop_id:
                unique_shops_in_report.add(order_product.shop_id)

            if prod_id not in sales_data:
                product = session.get(Product, prod_id)
                shop = (
                    session.get(Shop, order_product.shop_id)
                    if order_product.shop_id
                    else None
                )
                sales_data[prod_id] = {
                    "product_id": prod_id,
                    "product_name": product.name if product else "Unknown",
                    "product_sku": product.sku if product else "Unknown",
                    "shop_id": order_product.shop_id,
                    "shop_name": shop.name if shop else "Unknown",
                    "total_quantity_sold": 0,
                    "total_revenue": 0,
                    "average_price": 0,
                }

            sales_data[prod_id]["total_quantity_sold"] += quantity
            sales_data[prod_id]["total_revenue"] += revenue
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
                "total_orders": len(user_order_ids),
                "total_products_sold": total_products_sold,
                "total_revenue": total_revenue,
                "total_active_shops": total_active_shops,  # Total active shops (unfiltered)
                "shops_with_sales_in_interval": shops_with_sales_in_interval,  # Shops with sales in date range
                "shops_in_report_data": len(unique_shops_in_report),  # Shops that appear in the actual report data
                "distinct_customers": distinct_customers,  # Distinct customers in selected date period
            },
            "product_sales": list(sales_data.values()),
        }

        return api_response(200, "Sales report generated", report)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Sales report error: {error_details}")
        return api_response(500, f"Error generating sales report: {str(e)}")
@router.get("/old-shops-sales-report")
def get_sales_report(
    session: GetSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    shop_id: Optional[int] = None,  # Now filters by shop in order products
    product_id: Optional[int] = None,
    user: requireSignin = None,
):
    """Get sales report with product-wise sales data (filtered by user's shops)"""
    try:
        # Get user's permissions and shops
        user_permissions = user.get("permissions", [])
        user_shops = user.get("shops", [])
        user_shop_ids = [shop["id"] for shop in user_shops]
        is_admin = "system:*" in user_permissions

        # Validate shop access
        if shop_id:
            if not is_admin and shop_id not in user_shop_ids:
                return api_response(403, "You don't have access to this shop")

        # If not admin and no specific shop_id, user must have at least one shop
        if not is_admin and not user_shop_ids:
            return api_response(403, "You don't have any shops assigned")

        # Build query to get order IDs for completed orders
        order_query = select(Order.id).where(Order.order_status == OrderStatusEnum.COMPLETED)

        # Apply date filters
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            order_query = order_query.where(Order.created_at >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            order_query = order_query.where(Order.created_at <= end_dt)

        # Get order IDs - need to extract scalar values
        order_ids_result = session.exec(order_query).all()

        # Extract actual ID values from result
        order_ids = [row if isinstance(row, int) else row[0] for row in order_ids_result]

        if not order_ids:
            return api_response(200, "Sales report generated", {
                "period": {"start_date": start_date, "end_date": end_date},
                "summary": {
                    "total_orders": 0,
                    "total_products_sold": 0,
                    "total_revenue": 0,
                },
                "product_sales": [],
            })

        # Query order products directly
        op_query = select(OrderProduct).where(OrderProduct.order_id.in_(order_ids))

        # Apply shop filter based on user access
        if shop_id:
            # Specific shop requested (already validated above)
            op_query = op_query.where(OrderProduct.shop_id == shop_id)
        elif not is_admin:
            # Non-admin users: filter by their shops only
            op_query = op_query.where(OrderProduct.shop_id.in_(user_shop_ids))
        # Admin users without shop_id filter see all shops

        # Apply product filter if provided
        if product_id:
            op_query = op_query.where(OrderProduct.product_id == product_id)

        # Use scalars() to get proper OrderProduct instances
        order_products = session.exec(op_query).scalars().all()

        sales_data = {}
        total_revenue = 0
        total_products_sold = 0
        user_order_ids = set()  # Track unique orders containing user's shop products

        for order_product in order_products:
            prod_id = order_product.product_id
            quantity = float(order_product.order_quantity)
            revenue = order_product.subtotal

            # Track unique order IDs for user's shop products
            user_order_ids.add(order_product.order_id)

            if prod_id not in sales_data:
                product = session.get(Product, prod_id)
                shop = (
                    session.get(Shop, order_product.shop_id)
                    if order_product.shop_id
                    else None
                )
                sales_data[prod_id] = {
                    "product_id": prod_id,
                    "product_name": product.name if product else "Unknown",
                    "product_sku": product.sku if product else "Unknown",
                    "shop_id": order_product.shop_id,
                    "shop_name": shop.name if shop else "Unknown",
                    "total_quantity_sold": 0,
                    "total_revenue": 0,
                    "average_price": 0,
                }

            sales_data[prod_id]["total_quantity_sold"] += quantity
            sales_data[prod_id]["total_revenue"] += revenue
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
                "total_orders": len(user_order_ids),  # Only orders with user's shop products
                "total_products_sold": total_products_sold,
                "total_revenue": total_revenue,
            },
            "product_sales": list(sales_data.values()),
        }

        return api_response(200, "Sales report generated", report)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Sales report error: {error_details}")
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

        # 6. Log order cancellation transaction
        logger = TransactionLogger(session)
        for order_product in order.order_products:
            product = session.get(Product, order_product.product_id)
            if product:
                logger.log_order_cancelled(
                    order_id=order.id,
                    product_id=order_product.product_id,
                    quantity=int(float(order_product.order_quantity)),
                    unit_price=order_product.unit_price,
                    sale_price=order_product.sale_price,
                    user_id=user_id,
                    shop_id=order_product.shop_id,
                    notes=f"Order {order.tracking_number} cancelled - stock restored"
                )

        # 7. Send cancellation notifications + emails
        shop_ids = list(set([op.shop_id for op in order.order_products if op.shop_id]))
        cancelled_by = "admin" if is_admin else "customer"

        if order.customer_id:
            NotificationHelper.notify_order_cancelled(
                session=session,
                order_id=order.id,
                tracking_number=order.tracking_number,
                customer_id=order.customer_id,
                shop_ids=shop_ids,
                cancelled_by=cancelled_by
            )

        try:
            # Email customer
            customer_email = None
            if order.customer_id:
                customer = session.get(User, order.customer_id)
                if customer:
                    customer_email = customer.email
            cancel_reason = (request.reason if request and request.reason else "Not specified")
            cancel_amount = f"Rs.{float(order.paid_total):,.2f}" if order.paid_total else "N/A"
            if customer_email or order.customer_contact:
                send_email(
                    to_email=customer_email or order.customer_contact,
                    email_template_id=8,  # Order cancellation template
                    replacements={
                        "customer_name": order.customer_name,
                        "order_number": order.tracking_number,
                        "order_id": order.id,
                        "cancelled_by": cancelled_by,
                        "reason": cancel_reason,
                        "paid_total": f"Rs.{float(cancel_amount):,.2f}" if cancel_amount else "N/A",
                    },
                    session=session
                )

            # Email shop owners
            for shop_id in shop_ids:
                shop = session.get(Shop, shop_id)
                if shop:
                    shop_owner = session.get(User, shop.owner_id)
                    if shop_owner:
                        send_email(
                            to_email=shop_owner.email,
                            email_template_id=8,
                            replacements={
                                "customer_name": order.customer_name,
                                "order_number": order.tracking_number,
                                "order_id": order.id,
                                "shop_name": shop.name,
                                "cancelled_by": cancelled_by,
                                "reason": cancel_reason,
                                "paid_total": f"Rs.{float(cancel_amount):,.2f}" if cancel_amount else "N/A",
                            },
                            session=session
                        )

            # Email admins
            admin_users = session.exec(select(User).where(User.is_root == True)).all()
            for admin in admin_users:
                send_email(
                    to_email=admin.email,
                    email_template_id=8,
                    replacements={
                        "customer_name": order.customer_name,
                        "order_number": order.tracking_number,
                        "order_id": order.id,
                        "cancelled_by": cancelled_by,
                        "reason": cancel_reason,
                        "paid_total": f"Rs.{float(cancel_amount):,.2f}" if cancel_amount else "N/A",
                    },
                    session=session
                )
        except Exception as e:
            Print(f"Failed to send cancellation emails: {e}")

        Print(f"✅ Order {order_id} cancelled successfully")
        
        return OrderCancelResponse(
            message="Order cancelled successfully",
            order_id=order_id,
            status="cancelled",
            products_restocked=products_restocked,
            cancelled_at=now_pk(),
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
            cancelled_at=now_pk(),
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
    print(f"ordre:{order.order_status}")
    print(f"ordre:{OrderStatusEnum.COMPLETED}")

    # Only create earnings for completed orders
    if order.order_status != OrderStatusEnum.COMPLETED:
        return

    # Check if earnings already exist for this order (prevent duplicates)
    existing_earnings = session.exec(
        select(ShopEarning).where(ShopEarning.order_id == order.id)
    ).first()

    if existing_earnings:
        print(f"⚠️ Shop earnings already exist for order {order.id}, skipping creation")
        return

    # Get all order products for this order
    order_products = session.exec(
        select(OrderProduct).where(OrderProduct.order_id == order.id)
    ).scalars().all()
    print(f"order_products:{order_products}")

    if not order_products:
        print(f"⚠️ No order products found for order {order.id}")
        return

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
        print(f"delivery_fee_per_product:{delivery_fee_per_product}")
        shop_earning = (
            Decimal(str(order_product.subtotal))
            - order_product.admin_commission
            - delivery_fee_per_product
        )
        print(f"shop_earning:{shop_earning}")
        # Create shop earning record for this shop and product
        earning = ShopEarning(
            shop_id=order_product.shop_id,
            order_id=order.id,
            order_product_id=order_product.id,  # Link to specific order product
            order_amount=Decimal(str(order_product.subtotal)),
            admin_commission=order_product.admin_commission,
            shop_earning=shop_earning,
        )
        print(f"earning:{earning}")
        session.add(earning)


# ==========================================
# NEW: Role-based Order Statistics & Lists
# ==========================================
@router.get("/my-statistics")
def get_my_order_statistics(
    user: requireSignin,
    session: GetSession,
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
):
    """
    Get order statistics based on user role:
    - fulfillment role: Count orders assigned to user (fullfillment_id)
    - shop_admin role: Count orders from user's shops (includes cancelled/returned)
    - root role: Count all orders (includes cancelled/returned)
    
    Optional date range filtering using start_date and end_date parameters.
    If not provided, returns all-time statistics.
    """
    user_id = user.get("id")
    role_names = user.get("roles", [])
    
    # Determine role priority: root > shop_admin > fulfillment
    is_root = user.get("is_root", False) or "root" in role_names
    is_shop_admin = "shop_admin" in role_names or "Seller Roles" in role_names
    is_fulfillment = "fulfillment" in role_names or "Fulfillment" in role_names
    
    # Parse date range if provided
    date_conditions = []
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            date_conditions.append(Order.created_at >= start_dt)
        except ValueError:
            return api_response(400, f"Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            date_conditions.append(Order.created_at <= end_dt)
        except ValueError:
            return api_response(400, f"Invalid end_date format. Use YYYY-MM-DD")
    
    # Build base queries with date filters if provided
    def apply_date_filters(query):
        for condition in date_conditions:
            query = query.where(condition)
        return query
    
    completed_query = select(func.count(Order.id)).where(
        Order.order_status == OrderStatusEnum.COMPLETED
    )
    not_completed_query = select(func.count(Order.id)).where(
        Order.order_status != OrderStatusEnum.COMPLETED
    )
    
    # Apply date filters to base queries
    completed_query = apply_date_filters(completed_query)
    not_completed_query = apply_date_filters(not_completed_query)

    # Additional counts for shop_admin and root
    cancelled_count = 0
    returned_count = 0
    order_ids_with_shop = None  # Initialize for shop_admin use

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
        cancelled_query = apply_date_filters(cancelled_query)

        if is_shop_admin and order_ids_with_shop:
            cancelled_query = cancelled_query.where(Order.id.in_(order_ids_with_shop))

        cancelled_count = session.exec(cancelled_query).scalar() or 0

        # Count returned orders (order status = refunded)
        returned_query = select(func.count(Order.id)).where(
            Order.order_status == OrderStatusEnum.REFUNDED
        )
        returned_query = apply_date_filters(returned_query)

        if is_shop_admin and order_ids_with_shop:
            returned_query = returned_query.where(Order.id.in_(order_ids_with_shop))

        returned_count = session.exec(returned_query).scalar() or 0

    # Build response with date range info
    response_data = {
        "completed": completed_count,
        "not_completed": not_completed_count,
        "cancelled": cancelled_count,
        "returned": returned_count,
        "role": "root" if is_root else "shop_admin" if is_shop_admin else "fulfillment",
    }
    
    # Add date range to response if provided
    if start_date or end_date:
        response_data["date_range"] = {
            "start_date": start_date,
            "end_date": end_date,
        }

    return api_response(200, "Order statistics retrieved", response_data)
@router.get("/old-my-statistics")
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
    print(f"role_names:{user}")
    # Determine role priority: root > shop_admin > fulfillment
    is_root = user.get("is_root", False) or "root" in role_names
    is_shop_admin = "shop_admin" in role_names or "Seller Roles" in role_names
    is_fulfillment = "fulfillment" in role_names or "Fulfillment" in role_names
    #print(f"is_shop_admin:{is_shop_admin}")
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
    order_ids_with_shop = None  # Initialize for shop_admin use

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
    is_shop_admin = "shop_admin" in role_names  or "Seller Roles" in role_names
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
    is_shop_admin = "shop_admin" in role_names  or "Seller Roles" in role_names
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

@router.get("/myrecentorderproducts")
def get_my_recent_order_products(
    user: requireSignin,
    session: GetSession,
    dateRange: Optional[str] = None,
    numberRange: Optional[str] = None,
    searchTerm: str = None,
    columnFilters: Optional[str] = Query(None),
    order_status: Optional[OrderStatusEnum] = None,
    payment_status: Optional[PaymentStatusEnum] = None,
    shop_id: Optional[int] = None,
    shop_s_active: Optional[bool] = Query(None, description="Filter by shop active status"),
    product_type: Optional[OrderItemType] = None,
    limit_days: Optional[int] = Query(30, description="Number of days to look back for recent orders (default: 30)"),
    qty_eq: Optional[int] = Query(None, description="Filter by exact quantity"),
    qty_lt: Optional[int] = Query(None, description="Filter by quantity less than"),
    qty_gt: Optional[int] = Query(None, description="Filter by quantity greater than"),
    category_is_active: Optional[bool] = Query(None, description="Filter by category active status"),
    manufacturer_is_active: Optional[bool] = Query(None, description="Filter by manufacturer active status"),
    manufacturer_is_approved: Optional[bool] = Query(None, description="Filter by manufacturer approved status"),
    sort: Optional[str] = Query(None, description="Sort by column. Example: ['created_at','desc'] or ['product_name','asc']"),
    page: int = None,
    skip: int = 0,
    limit: int = Query(50, ge=1, le=200, description="Number of products to return (default: 50)"),
):
    """
    Get products from the authenticated user's recent orders with full product details.
    """
    
    try:
        # Get user ID from the dictionary
        if not isinstance(user, dict):
            return api_response(401, "Invalid user object")
        
        user_id = user.get('id')
        if not user_id:
            return api_response(401, "User ID not found")
        
        print(f"✅ User ID: {user_id}")
        
        # Calculate date threshold for recent orders
        threshold_date = None
        if not dateRange and limit_days:
            from datetime import datetime, timedelta
            threshold_date = datetime.now() - timedelta(days=limit_days)
            threshold_date_str = threshold_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # Build WHERE clause for orders
        order_where = f"customer_id = {user_id}"
        
        # Apply date range filter
        if dateRange:
            try:
                import ast
                date_range = ast.literal_eval(dateRange) if isinstance(dateRange, str) else dateRange
                if len(date_range) >= 3:
                    start_date = date_range[1]
                    end_date = date_range[2]
                    if start_date and end_date:
                        order_where += f" AND created_at BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'"
            except Exception as e:
                print(f"Error parsing dateRange: {e}")
        elif threshold_date:
            order_where += f" AND created_at >= '{threshold_date_str}'"
        
        # Apply order status filter
        if order_status:
            order_where += f" AND order_status = '{order_status.value}'"
        
        # Apply payment status filter
        if payment_status:
            order_where += f" AND payment_status = '{payment_status.value}'"
        
        # Get orders
        orders_query = f"SELECT * FROM orders WHERE {order_where} ORDER BY created_at DESC"
        print(f"Orders query: {orders_query}")
        
        orders_result = session.exec(text(orders_query)).all()
        
        # Convert orders to list of dicts
        orders = []
        for row in orders_result:
            if hasattr(row, '_mapping'):
                orders.append(dict(row._mapping))
            else:
                orders.append(dict(row))
        
        print(f"Found {len(orders)} orders")
        
        if not orders:
            return api_response(200, "No recent orders found", [], 0)
        
        # Get order IDs
        order_ids = [str(order['id']) for order in orders if order.get('id')]
        order_ids_str = ','.join(order_ids)
        
        # Build WHERE clause for order products
        conditions = [f"op.order_id IN ({order_ids_str})"]
        
        # Apply shop filter
        if shop_id:
            conditions.append(f"op.shop_id = {shop_id}")
        if shop_s_active is not None:
            bool_value = "TRUE" if shop_s_active else "FALSE"
            conditions.append(f"(s.id IS NULL OR s.is_active = {bool_value})")
        
        # Apply product type filter
        if product_type:
            conditions.append(f"op.item_type = '{product_type.value}'")
        
        # Apply quantity filters
        if qty_eq is not None:
            conditions.append(f"CAST(op.order_quantity AS DECIMAL) = {qty_eq}")
        if qty_lt is not None:
            conditions.append(f"CAST(op.order_quantity AS DECIMAL) < {qty_lt}")
        if qty_gt is not None:
            conditions.append(f"CAST(op.order_quantity AS DECIMAL) > {qty_gt}")
        
        # Apply searchTerm
        if searchTerm:
            conditions.append(f"""(COALESCE(p.name, '') ILIKE '%{searchTerm}%' OR COALESCE(p.description, '') ILIKE '%{searchTerm}%' OR COALESCE(p.sku, '') ILIKE '%{searchTerm}%')""")
        
        # Apply category_is_active filter
        if category_is_active is not None:
            bool_value = "TRUE" if category_is_active else "FALSE"
            conditions.append(f"(c.id IS NULL OR c.is_active = {bool_value})")
        
        # Apply manufacturer filters
        if manufacturer_is_active is not None:
            bool_value = "TRUE" if manufacturer_is_active else "FALSE"
            conditions.append(f"(m.id IS NULL OR m.is_active = {bool_value})")
        
        if manufacturer_is_approved is not None:
            bool_value = "TRUE" if manufacturer_is_approved else "FALSE"
            conditions.append(f"(m.id IS NULL OR m.is_approved = {bool_value})")
        
        # Apply numberRange filter
        if numberRange:
            try:
                import ast
                number_range = ast.literal_eval(numberRange) if isinstance(numberRange, str) else numberRange
                column_name = number_range[0]
                min_val = number_range[1] if len(number_range) > 1 else None
                max_val = number_range[2] if len(number_range) > 2 else None
                
                if min_val is not None and max_val is not None:
                    conditions.append(f"op.{column_name} BETWEEN {min_val} AND {max_val}")
                elif min_val is not None:
                    conditions.append(f"op.{column_name} >= {min_val}")
                elif max_val is not None:
                    conditions.append(f"op.{column_name} <= {max_val}")
            except Exception as e:
                print(f"Error parsing numberRange: {e}")
        
        # Combine all conditions with AND
        op_where = " AND ".join(conditions) if conditions else "1=1"
        
        # Build ORDER BY clause
        order_by = "ORDER BY o.created_at DESC"  # Default
        
        if sort:
            try:
                import ast
                sort_param = ast.literal_eval(sort) if isinstance(sort, str) else sort
                column_name, direction = sort_param[0], sort_param[1]
                
                if column_name == "product_name":
                    order_by = f"ORDER BY p.name {direction} NULLS LAST"
                elif column_name == "shop_name":
                    order_by = f"ORDER BY s.name {direction} NULLS LAST"
                elif column_name == "order_date":
                    order_by = f"ORDER BY o.created_at {direction} NULLS LAST"
                elif column_name == "quantity":
                    order_by = f"ORDER BY CAST(op.order_quantity AS DECIMAL) {direction} NULLS LAST"
                elif column_name in ["unit_price", "subtotal", "item_discount", "item_tax"]:
                    order_by = f"ORDER BY op.{column_name} {direction} NULLS LAST"
            except Exception as e:
                print(f"Error parsing sort: {e}")
        
        # Get total count
        count_query = f"""
            SELECT COUNT(DISTINCT op.id) as total
            FROM order_product op
            LEFT JOIN products p ON op.product_id = p.id
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
            WHERE {op_where}
        """
        
        print(f"Count query: {count_query}")
        
        count_result = session.exec(text(count_query)).first()
        total_products = count_result[0] if count_result else 0
        
        # Main query with all product attributes
        main_query = f"""
            SELECT 
                -- Order product details
                op.id as order_product_id,
                op.order_id,
                op.product_id,
                op.variation_option_id,
                op.order_quantity,
                op.unit_price as order_unit_price,
                op.sale_price as order_sale_price,
                op.subtotal,
                op.item_discount,
                op.item_tax,
                op.admin_commission,
                op.item_type,
                op.variation_data,
                op.product_snapshot,
                op.variation_snapshot,
                op.shop_id,
                op.review_id,
                op.is_returned,
                op.returned_quantity,
                
                -- Order details
                o.tracking_number as order_tracking_number,
                o.created_at as order_date,
                o.order_status,
                o.payment_status,
                
                -- Product details (all attributes from products table)
                p.id,
                p.name,
                p.slug,
                p.description,
                p.price,
                p.sale_price,
                p.max_price,
                p.min_price,
                p.purchase_price,
                p.weight,
                p.image,
                p.gallery,
                p.is_active,
                p.is_feature,
                p.quantity,
                p.status,
                p.product_type,
                p.unit,
                p.dimension_unit,
                p.sku,
                p.bar_code,
                p.height,
                p.width,
                p.length,
                p.warranty,
                p.meta_title,
                p.meta_description,
                p.return_policy,
                p.shipping_info,
                p.tags,
                p.attributes,
                p.total_purchased_quantity,
                p.total_sold_quantity,
                p.rating,
                p.review_count,
                
                -- Category details
                c.id as category_id,
                c.name as category_name,
                c.slug as category_slug,
                c.root_id as category_root_id,
                c.parent_id as category_parent_id,
                c.is_active as category_is_active,
                
                -- Shop details
                s.id as shop_id,
                s.name as shop_name,
                s.slug as shop_slug,
                s.is_active as shop_is_active,
                
                -- Manufacturer details
                p.manufacturer_id,
                m.name as manufacturer_name,
                m.is_active as manufacturer_is_active,
                
                -- Variation details (if any)
                vo.id as variation_id,
                vo.title as variation_title,
                vo.options as variation_options,
                vo.sku as variation_sku,
                vo.image as variation_image,
                vo.price as variation_price,
                vo.sale_price as variation_sale_price,
                vo.quantity as variation_quantity
                
            FROM order_product op
            LEFT JOIN orders o ON op.order_id = o.id
            LEFT JOIN products p ON op.product_id = p.id
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN shops s ON op.shop_id = s.id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
            LEFT JOIN variation_options vo ON op.variation_option_id = vo.id
            WHERE {op_where}
            {order_by}
            LIMIT {limit} OFFSET {skip}
        """
        
        print(f"Main query: {main_query}")
        
        results = session.exec(text(main_query)).all()
        
        # Build response data
        products_data = []
        
        for row in results:
            if hasattr(row, '_mapping'):
                row_dict = dict(row._mapping)
            else:
                row_dict = dict(row)
            
            # Parse JSON fields
            image = row_dict.get('image')
            if image and isinstance(image, str):
                try:
                    import json
                    image = json.loads(image)
                except:
                    pass
            
            gallery = row_dict.get('gallery')
            if gallery and isinstance(gallery, str):
                try:
                    import json
                    gallery = json.loads(gallery)
                except:
                    pass
            
            tags = row_dict.get('tags')
            if tags and isinstance(tags, str):
                try:
                    import json
                    tags = json.loads(tags)
                except:
                    pass
            
            attributes = row_dict.get('attributes')
            if attributes and isinstance(attributes, str):
                try:
                    import json
                    attributes = json.loads(attributes)
                except:
                    pass
            
            # Build variation options list
            variation_options = []
            if row_dict.get('variation_id'):
                variation_options.append({
                    "id": row_dict.get('variation_id'),
                    "title": row_dict.get('variation_title'),
                    "price": str(row_dict.get('variation_price')) if row_dict.get('variation_price') else None,
                    "sale_price": str(row_dict.get('variation_sale_price')) if row_dict.get('variation_sale_price') else None,
                    "quantity": row_dict.get('variation_quantity', 0),
                    "options": row_dict.get('variation_options'),
                    "image": row_dict.get('variation_image'),
                    "sku": row_dict.get('variation_sku'),
                    "is_active": True
                })
            
            # Build category object
            category = {
                "id": row_dict.get('category_id'),
                "name": row_dict.get('category_name'),
                "slug": row_dict.get('category_slug'),
                "root_id": row_dict.get('category_root_id'),
                "parent_id": row_dict.get('category_parent_id'),
                "is_active": row_dict.get('category_is_active')
            } if row_dict.get('category_id') else None
            
            # Build shop object
            shop = {
                "id": row_dict.get('shop_id'),
                "name": row_dict.get('shop_name'),
                "slug": row_dict.get('shop_slug'),
                "is_active": row_dict.get('shop_is_active')
            } if row_dict.get('shop_id') else None
            
            # Build manufacturer object
            manufacturer = {
                "id": row_dict.get('manufacturer_id'),
                "name": row_dict.get('manufacturer_name'),
                "is_active": row_dict.get('manufacturer_is_active')
            } if row_dict.get('manufacturer_id') else None
            
            # Calculate total quantity (product quantity + variation quantities)
            total_quantity = row_dict.get('quantity', 0) or 0
            if variation_options:
                for var in variation_options:
                    total_quantity += var.get('quantity', 0)
            
            product_data = {
                # Order context (keeping this for reference)
                "order_product_id": row_dict.get('order_product_id'),
                "order_id": row_dict.get('order_id'),
                "order_tracking_number": row_dict.get('order_tracking_number'),
                "order_date": str(row_dict.get('order_date')) if row_dict.get('order_date') else None,
                "order_status": row_dict.get('order_status'),
                "payment_status": row_dict.get('payment_status'),
                
                # Purchase details from order
                "purchase_quantity": float(row_dict.get('order_quantity', 0)) if row_dict.get('order_quantity') else 0,
                "purchase_unit_price": float(row_dict.get('order_unit_price', 0)) if row_dict.get('order_unit_price') else 0,
                "purchase_sale_price": float(row_dict.get('order_sale_price', 0)) if row_dict.get('order_sale_price') else None,
                "purchase_subtotal": float(row_dict.get('subtotal', 0)) if row_dict.get('subtotal') else 0,
                
                # Full product details (matching your desired format)
                "id": row_dict.get('id'),
                "name": row_dict.get('name'),
                "slug": row_dict.get('slug'),
                "description": row_dict.get('description'),
                "price": str(row_dict.get('price')) if row_dict.get('price') else None,
                "sale_price": str(row_dict.get('sale_price')) if row_dict.get('sale_price') else None,
                "max_price": str(row_dict.get('max_price')) if row_dict.get('max_price') else None,
                "min_price": str(row_dict.get('min_price')) if row_dict.get('min_price') else None,
                "purchase_price": str(row_dict.get('purchase_price')) if row_dict.get('purchase_price') else None,
                "weight": float(row_dict.get('weight')) if row_dict.get('weight') else None,
                "image": image,
                "gallery": gallery,
                "is_active": row_dict.get('is_active', False),
                "is_feature": row_dict.get('is_feature'),
                "quantity": row_dict.get('quantity', 0) or 0,
                "status": row_dict.get('status'),
                "product_type": row_dict.get('product_type'),
                "unit": row_dict.get('unit'),
                "dimension_unit": row_dict.get('dimension_unit'),
                "sku": row_dict.get('sku'),
                "bar_code": row_dict.get('bar_code'),
                "height": float(row_dict.get('height')) if row_dict.get('height') else None,
                "width": float(row_dict.get('width')) if row_dict.get('width') else None,
                "length": float(row_dict.get('length')) if row_dict.get('length') else None,
                "warranty": row_dict.get('warranty'),
                "meta_title": row_dict.get('meta_title'),
                "meta_description": row_dict.get('meta_description'),
                "return_policy": row_dict.get('return_policy'),
                "shipping_info": row_dict.get('shipping_info'),
                "tags": tags,
                "attributes": attributes,
                "variation_options": variation_options,
                "total_purchased_quantity": row_dict.get('total_purchased_quantity', 0) or 0,
                "total_sold_quantity": row_dict.get('total_sold_quantity', 0) or 0,
                "current_stock_value": None,  # Calculate if needed
                "rating": float(row_dict.get('rating', 0)) if row_dict.get('rating') else 0,
                "review_count": row_dict.get('review_count', 0) or 0,
                "total_quantity": total_quantity,
                "variations_count": len(variation_options),
                
                # Related objects
                "category": category,
                "shop": shop,
                "manufacturer": manufacturer,
                
                # Variation details from order (if applicable)
                "variation_option_id": row_dict.get('variation_option_id'),
                "variation_details": {
                    "id": row_dict.get('variation_id'),
                    "title": row_dict.get('variation_title'),
                    "options": row_dict.get('variation_options'),
                    "sku": row_dict.get('variation_sku'),
                    "image": row_dict.get('variation_image'),
                } if row_dict.get('variation_id') else None,
                
                # Additional order product info
                "item_discount": float(row_dict.get('item_discount', 0)) if row_dict.get('item_discount') else 0,
                "item_tax": float(row_dict.get('item_tax', 0)) if row_dict.get('item_tax') else 0,
                "admin_commission": float(row_dict.get('admin_commission', 0)) if row_dict.get('admin_commission') else 0,
                "review_id": row_dict.get('review_id'),
                "is_returned": row_dict.get('is_returned', False),
                "returned_quantity": row_dict.get('returned_quantity', 0),
            }
            
            products_data.append(product_data)
        
        return api_response(
            200,
            f"Found {len(products_data)} products from {len(orders)} orders",
            products_data,
            total_products
        )
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return api_response(500, f"Error: {str(e)}")