# src/api/routes/orderRoute.py
import ast
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query
from sqlalchemy import select,func
from src.api.models.cart_model.cartModel import Cart
from src.api.core.utility import Print, uniqueSlugify
from src.api.core.operation import listop, updateOp
from src.api.core.response import api_response, raiseExceptions
from sqlalchemy.orm import selectinload, joinedload
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
)
from src.api.models.product_model.productsModel import Product, ProductRead, ProductType
from src.api.models.product_model.variationOptionModel import VariationOption
from src.api.models.category_model import Category
from src.api.models.shop_model.shopsModel import Shop
from src.api.models.withdrawModel import ShopEarning
from src.api.core.dependencies import (
    GetSession,
    requirePermission,
    requireSignin,
    isAuthenticated,
)
from datetime import datetime, timezone
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
        commission_amount = (unit_price * quantity) * (
            category.admin_commission_rate / 100
        )

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


# @router.post("/cartcreate")
# def create(request: OrderCartCreate, session: GetSession, user: isAuthenticated = None):
#     cart_items = request.cart or []
#     shipping_address = request.shipping_address
#     # ✅ 1. Validate cart data
#     if not isinstance(cart_items, list) or not cart_items:
#         return api_response(400, "Cart cannot be empty")

#     product_ids = [
#         item.product_id for item in cart_items if item.product_id and item.product_id
#     ]
#     # cart_ids = [item.id for item in cart_items if item.id]

#     if not product_ids:
#         return api_response(400, "Each cart item must include a valid product ID")

#     # ✅ 2. Validate products exist in db
#     products = (
#         session.exec(select(Product).where(Product.id.in_(product_ids))).scalars().all()
#     )
#     if len(products) != len(product_ids):
#         found = {p.id for p in products}
#         missing = [pid for pid in product_ids if pid not in found]
#         return api_response(404, f"Product(s) not found: {missing}")

#     # ✅ 3. Validate carts if user is authenticated
#     carts = []
#     if user:
#         carts = (
#             session.exec(
#                 select(Cart)
#                 .where(Cart.user_id == user["id"])
#                 .where(Cart.product_id.in_(product_ids))
#             )
#             .scalars()
#             .all()
#         )
#         if len(carts) != len(product_ids):
#             found_ids = {c.product_id for c in carts}
#             missing = [pid for pid in product_ids if pid not in found_ids]
#             return api_response(
#                 404, f"Cart item(s) not found for product(s): {missing}"
#             )

#     # ✅ 4. Calculate totals
#     amount = 0.0
#     for item in cart_items:
#         product = next((p for p in products if p.id == item.product_id), None)
#         if not product:
#             continue
#         # use sale_price if > 0 else price
#         price = (
#             product.sale_price
#             if product.sale_price and product.sale_price > 0
#             else product.price
#         )
#         amount += price * item.quantity

#     total = amount  # add tax or discount later

#     # ✅ 5. Build order fields
#     tracking_number = f"TRK-{uuid.uuid4().hex[:10].upper()}"
#     order = Order(
#         tracking_number=tracking_number,
#         customer_id=user["id"] if user else None,
#         customer_contact=shipping_address.get("phone"),
#         customer_name=shipping_address.get("name"),
#         amount=amount,
#         total=total,
#         shipping_address=shipping_address,
#         billing_address=shipping_address,  # same for now
#         order_status="order-pending",
#         payment_status="payment-cash-on-delivery",
#         language="en",
#     )

#     session.add(order)
#     session.flush()

#     # ✅ 6. Create order products
#     order_products = []
#     for item in cart_items:
#         product = next((p for p in products if p.id == item.product_id), None)
#         if not product:
#             continue

#         price = (
#             product.sale_price
#             if product.sale_price and product.sale_price > 0
#             else product.price
#         )
#         subtotal = price * item.quantity

#         op = OrderProduct(
#             order_id=order.id,
#             product_id=product.id,
#             order_quantity=str(item.quantity),
#             unit_price=price,
#             subtotal=subtotal,
#             admin_commission=0.00,
#         )
#         order_products.append(op)

#     session.add_all(order_products)
#     session.commit()

#     # ✅ 7. Return result
#     products_data = [ProductRead.model_validate(p).model_dump() for p in products]
#     return api_response(
#         200,
#         "Order created successfully",
#         {
#             "order_id": order.id,
#             "tracking_number": tracking_number,
#             "order_type": "offline" if not user else "user",
#             "total": total,
#             "items": len(order_products),
#             "products": products_data,
#         },
#     )

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

    # ✅ 4. Calculate totals and validate variable products
    amount = 0.0
    validation_errors = []
    
    for item in cart_items:
        product = next((p for p in products if p.id == item.product_id), None)
        if not product:
            validation_errors.append(f"Product {item.product_id} not found")
            continue
        
        # 🔥 FIX: Convert quantity to float (to handle decimal quantities if needed)
        try:
            quantity = float(item.quantity)
        except (ValueError, TypeError):
            validation_errors.append(f"Invalid quantity for product {product.name}: {item.quantity}")
            continue
            
        # 🔥 NEW: Handle variable products
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
                
            # 🔥 FIX: Convert variation price to float
            price = float(
                variation.sale_price
                if variation.sale_price and variation.sale_price > 0
                else variation.price
            )
        else:
            # Handle simple product
            if product.quantity < quantity:
                validation_errors.append(f"Insufficient stock for {product.name}. Available: {product.quantity}, Requested: {quantity}")
                continue
                
            # 🔥 FIX: Convert product price to float
            price = float(
                product.sale_price
                if product.sale_price and product.sale_price > 0
                else product.price
            )
            
        amount += price * quantity  # 🔥 FIX: Now both are numeric

    if validation_errors:
        return api_response(400, "Product validation failed", {"errors": validation_errors})

    total = amount  # add tax or discount later

    # ✅ 5. Build order fields
    tracking_number = generate_tracking_number()
    order = Order(
        tracking_number=tracking_number,
        customer_id=user["id"] if user else None,
        customer_contact=shipping_address.get("phone"),
        customer_name=shipping_address.get("name"),
        amount=amount,
        total=total,
        shipping_address=shipping_address,
        billing_address=shipping_address,  # same for now
        order_status="order-pending",
        payment_status="payment-cash-on-delivery",
        language="en",
    )

    session.add(order)
    session.flush()

    # 🔥 NEW: Initialize total admin commission
    total_admin_commission = Decimal("0.00")

    # ✅ 6. Create order products with variable product support
    order_products = []
    for item in cart_items:
        product = next((p for p in products if p.id == item.product_id), None)
        if not product:
            continue

        # 🔥 FIX: Convert quantity to float
        try:
            quantity = float(item.quantity)
        except (ValueError, TypeError):
            continue

        # 🔥 UPDATED: Determine product type and pricing
        item_type = OrderItemType.VARIABLE if item.variation_option_id else OrderItemType.SIMPLE
        
        # 🔥 NEW: Create product and variation snapshots
        product_snapshot = get_product_snapshot(session, product.id)
        variation_snapshot = None
        
        if item_type == OrderItemType.VARIABLE:
            variation = session.get(VariationOption, item.variation_option_id)
            if not variation:
                continue
                
            # 🔥 FIX: Convert variation price to float
            price = float(
                variation.sale_price
                if variation.sale_price and variation.sale_price > 0
                else variation.price
            )
            
            # 🔥 NEW: Create variation snapshot
            variation_snapshot = get_variation_snapshot(session, item.variation_option_id)
            variation_data = {
                "id": variation.id,
                "title": variation.title,
                "options": variation.options,
            } if variation else None
        else:
            # 🔥 FIX: Convert product price to float
            price = float(
                product.sale_price
                if product.sale_price and product.sale_price > 0
                else product.price
            )
            variation_data = None

        subtotal = price * quantity
        
        # 🔥 NEW: Calculate admin commission for this product
        admin_commission = calculate_admin_commission(
            session, product.id, price, str(quantity)
        )
        total_admin_commission += admin_commission
        
        # 🔥 UPDATED: Create OrderProduct with all new attributes
        op = OrderProduct(
            order_id=order.id,
            product_id=product.id,
            variation_option_id=item.variation_option_id,
            order_quantity=str(quantity),
            unit_price=price,
            subtotal=subtotal,
            admin_commission=admin_commission,  # 🔥 NEW: Store calculated commission
            item_type=item_type,
            variation_data=variation_data,
            shop_id=product.shop_id,
            product_snapshot=product_snapshot,  # 🔥 NEW: Store product snapshot
            variation_snapshot=variation_snapshot,  # 🔥 NEW: Store variation snapshot
        )
        order_products.append(op)

    session.add_all(order_products)
    
    # 🔥 NEW: Update order with total admin commission
    order.admin_commission_amount = total_admin_commission
    session.add(order)
    
    # 🔥 NEW: Create initial order status history
    order_status = OrderStatus(order_id=order.id, order_pending_date=datetime.now())
    session.add(order_status)
    
    # 🔥 NEW: Update inventory using the proper update_product_inventory function
    for item in cart_items:
        product = next((p for p in products if p.id == item.product_id), None)
        if not product:
            continue
        
        # Create OrderProductCreate object for inventory update
        product_data = OrderProductCreate(
            product_id=item.product_id,
            variation_option_id=item.variation_option_id,
            order_quantity=str(item.quantity),
            unit_price=0.0,  # This will be set properly in the actual OrderProduct
            subtotal=0.0,    # This will be set properly in the actual OrderProduct
            item_type=OrderItemType.VARIABLE if item.variation_option_id else OrderItemType.SIMPLE,
            shop_id=product.shop_id,
        )
        
        # 🔥 NEW: Use the centralized update_product_inventory function
        update_product_inventory(session, product_data, "deduct")

    session.commit()

    # ✅ 7. Return result
    products_data = []
    for product in products:
        product_data = ProductRead.model_validate(product).model_dump()
        # 🔥 NEW: Include variation information in response if applicable
        cart_item = next((item for item in cart_items if item.product_id == product.id), None)
        if cart_item and cart_item.variation_option_id:
            variation = session.get(VariationOption, cart_item.variation_option_id)
            if variation:
                product_data["selected_variation"] = {
                    "id": variation.id,
                    "title": variation.title,
                    "options": variation.options,
                }
        products_data.append(product_data)
        
    return api_response(
        200,
        "Order created successfully",
        {
            "order_id": order.id,
            "tracking_number": tracking_number,
            "order_type": "offline" if not user else "user",
            "total": total,
            "items": len(order_products),
            "products": products_data,
        },
    )
@router.post("/create-from-cart")
def create_order_from_cart(
    request: OrderCartCreate, 
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
    
    required_address_fields = ["name", "phone", "address", "city", "country"]
    missing_fields = [field for field in required_address_fields if not shipping_address.get(field)]
    if missing_fields:
        return api_response(400, f"Missing required shipping address fields: {', '.join(missing_fields)}")
    
    # ✅ 2. Get user's cart items
    cart_items = session.exec(
        select(Cart).where(Cart.user_id == user_id)
    ).all()
    
    if not cart_items:
        return api_response(400, "Cart is empty")
    
    # ✅ 3. Validate cart items and prepare order products
    product_ids = [item.product_id for item in cart_items]
    products = session.exec(
        select(Product).where(Product.id.in_(product_ids))
    ).all()
    
    # Create product lookup dictionary
    product_dict = {product.id: product for product in products}
    
    # ✅ 4. Validate all cart items and calculate totals
    amount = 0.0
    validation_errors = []
    order_products_data = []
    
    for cart_item in cart_items:
        product = product_dict.get(cart_item.product_id)
        if not product:
            validation_errors.append(f"Product {cart_item.product_id} not found")
            continue
        
        if not product.is_active:
            validation_errors.append(f"Product {product.name} is not active")
            continue
        
        # Determine product type and validate availability
        item_type = OrderItemType.VARIABLE if cart_item.variation_option_id else OrderItemType.SIMPLE
        
        try:
            quantity = float(cart_item.quantity)
        except (ValueError, TypeError):
            validation_errors.append(f"Invalid quantity for product {product.name}: {cart_item.quantity}")
            continue
        
        # Validate variable products
        if item_type == OrderItemType.VARIABLE:
            variation = session.get(VariationOption, cart_item.variation_option_id)
            if not variation:
                validation_errors.append(f"Variation option {cart_item.variation_option_id} not found")
                continue
            
            if variation.product_id != product.id:
                validation_errors.append(f"Variation {cart_item.variation_option_id} does not belong to product {product.id}")
                continue
            
            # Check variation stock
            if variation.quantity < quantity:
                validation_errors.append(f"Insufficient stock for variation {variation.title}. Available: {variation.quantity}, Requested: {quantity}")
                continue
            
            # Get variation price
            price = float(
                variation.sale_price
                if variation.sale_price and variation.sale_price > 0
                else variation.price
            )
            
            variation_data = {
                "id": variation.id,
                "title": variation.title,
                "options": variation.options,
            }
            
        else:
            # Validate simple product
            if product.quantity < quantity:
                validation_errors.append(f"Insufficient stock for {product.name}. Available: {product.quantity}, Requested: {quantity}")
                continue
            
            # Get product price
            price = float(
                product.sale_price
                if product.sale_price and product.sale_price > 0
                else product.price
            )
            variation_data = None
        
        subtotal = price * quantity
        amount += subtotal
        
        # Prepare order product data
        order_product_data = OrderProductCreate(
            product_id=product.id,
            variation_option_id=cart_item.variation_option_id,
            order_quantity=str(quantity),
            unit_price=price,
            subtotal=subtotal,
            item_type=item_type,
            variation_data=variation_data,
            shop_id=product.shop_id,
        )
        order_products_data.append(order_product_data)
    
    if validation_errors:
        return api_response(400, "Cart validation failed", {"errors": validation_errors})
    
    # ✅ 5. Create order
    total = amount  # Can add tax, discount, delivery fee later
    tracking_number = generate_tracking_number()
    
    order = Order(
        tracking_number=tracking_number,
        customer_id=user_id,
        customer_contact=shipping_address.get("phone"),
        customer_name=shipping_address.get("name"),
        amount=amount,
        total=total,
        shipping_address=shipping_address,
        billing_address=shipping_address,  # Same as shipping for now
        order_status=OrderStatusEnum.PENDING.value,
        payment_status=PaymentStatusEnum.PENDING.value,
        language="en",
    )
    
    session.add(order)
    session.flush()
    
    # ✅ 6. Create order products with snapshots and commissions
    total_admin_commission = Decimal("0.00")
    created_order_products = []
    
    for product_data in order_products_data:
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
            **product_data.model_dump(),
            order_id=order.id,
            admin_commission=admin_commission,
            product_snapshot=product_snapshot,
            variation_snapshot=variation_snapshot,
        )
        session.add(order_product)
        created_order_products.append(order_product)
        
        # Update inventory
        update_product_inventory(session, product_data, "deduct")
    
    # ✅ 7. Update order with total admin commission
    order.admin_commission_amount = total_admin_commission
    session.add(order)
    
    # ✅ 8. Create initial order status history
    order_status = OrderStatus(order_id=order.id, order_pending_date=datetime.now())
    session.add(order_status)
    
    # ✅ 9. CLEAR USER'S CART after successful order creation
    try:
        # Delete all cart items for this user
        delete_stmt = select(Cart).where(Cart.user_id == user_id)
        user_cart_items = session.exec(delete_stmt).all()
        
        for cart_item in user_cart_items:
            session.delete(cart_item)
        
        # Commit all changes (order creation + cart clearance)
        session.commit()
        
    except Exception as e:
        # Rollback if cart clearance fails
        session.rollback()
        return api_response(500, f"Order created but failed to clear cart: {str(e)}")
    
    # ✅ 10. Prepare response data
    products_data = []
    for product in products:
        product_data = ProductRead.model_validate(product).model_dump()
        # Include variation information if applicable
        cart_item = next((item for item in cart_items if item.product_id == product.id), None)
        if cart_item and cart_item.variation_option_id:
            variation = session.get(VariationOption, cart_item.variation_option_id)
            if variation:
                product_data["selected_variation"] = {
                    "id": variation.id,
                    "title": variation.title,
                    "options": variation.options,
                }
        products_data.append(product_data)
    
    return api_response(
        201,
        "Order created successfully from cart and cart cleared",
        {
            "order_id": order.id,
            "tracking_number": tracking_number,
            "total": total,
            "items": len(created_order_products),
            "products": products_data,
            "cart_cleared": True,
            "cart_items_removed": len(user_cart_items),
        },
    )

@router.post("/create")
def create(request: OrderCreate, session: GetSession):
    # Validate all products before creating order
    validation_errors = []
    shops_in_order = set()  # Track unique shops in this order

    for product_data in request.order_products:
        is_available, message = validate_product_availability(session, product_data)
        if not is_available:
            validation_errors.append(f"Product {product_data.product_id}: {message}")
        else:
            # Add shop to unique shops set
            if product_data.shop_id:
                shops_in_order.add(product_data.shop_id)

    if validation_errors:
        return api_response(
            400, "Product availability issues", {"errors": validation_errors}
        )

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
            variation_snapshot = get_variation_snapshot(
                session, product_data.variation_option_id
            )

        # Create order product with shop_id
        order_product = OrderProduct(
            **product_data.model_dump(),
            order_id=order.id,
            admin_commission=admin_commission,
            product_snapshot=product_snapshot,
            variation_snapshot=variation_snapshot,
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
    )

    if not result["data"]:
        return api_response(404, "No orders found")

    # Enhance each order with shop information
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
        for shop_id in shops:
            shop = session.get(Shop, shop_id)
            if shop:
                shop_details.append(
                    {"id": shop.id, "name": shop.name, "slug": shop.slug}
                )

        order_data.shops = shop_details
        order_data.shop_count = len(shop_details)
        enhanced_orders.append(order_data)

    return api_response(200, "Orders found", enhanced_orders, result["total"])

@router.get(
    "/listorder",
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
    )

    if not result["data"]:
        return api_response(404, "No orders found")

    # Enhance each order with shop information
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
        for shop_id in shops:
            shop = session.get(Shop, shop_id)
            if shop:
                shop_details.append(
                    {"id": shop.id, "name": shop.name, "slug": shop.slug}
                )

        order_data.shops = shop_details
        order_data.shop_count = len(shop_details)
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
