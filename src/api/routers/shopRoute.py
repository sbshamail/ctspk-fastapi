from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Query
from sqlalchemy import func
from sqlmodel import select

from src.api.core.utility import uniqueSlugify
from src.api.models.shop_model import (
    Shop,
    ShopCreate,
    ShopRead,
    ShopReadWithEarnings,
    ShopUpdate,
    ShopVerifyByAdmin,
)
from src.api.models.withdrawModel import ShopEarning
from src.api.models.product_model.productsModel import Product
from src.api.models.order_model.orderModel import OrderProduct
from sqlalchemy import or_

from src.api.models.role_model.userRoleModel import UserRole
from src.api.models.role_model.roleModel import Role
from src.api.core import (
    GetSession,
    ListQueryParams,
    listRecords,
    requireSignin,
    requirePermission,
    updateOp,
)
from src.api.core.response import api_response, raiseExceptions
from src.api.core.middleware import handle_async_wrapper
from src.api.core.notification_helper import NotificationHelper

router = APIRouter(prefix="/shop", tags=["Shop"])


# ✅ CREATE shop
@router.post("/create")
def create_shop(
    user: requireSignin,  # the logged-in user
    request: ShopCreate,
    session: GetSession,
):
    with session.begin():  # 🔑 single transaction

        # 1️⃣ Create the shop
        data = Shop(**request.model_dump(), owner_id=user.get("id"))
        data.slug = uniqueSlugify(session, Shop, data.name)
        session.add(data)

        # 2️⃣ find the shop_admin role
        role = session.exec(select(Role).where(Role.slug == "shop_admin")).first()
        raiseExceptions((role, 404, "Role not found"))

        # 3️⃣ Assign the shop_admin role to the user (if not already assigned)
        existing = session.exec(
            select(UserRole).where(
                UserRole.user_id == user.get("id"),
                UserRole.role_id == role.id,
            )
        ).first()

        if not existing:
            mapping = UserRole(user_id=user.get("id"), role_id=role.id)
            session.add(mapping)

    # 🔒 commit happens automatically on context exit, rollback on error
    session.refresh(data)

    # Send notifications
    NotificationHelper.notify_shop_created(
        session=session,
        shop_id=data.id,
        shop_name=data.name
    )

    read = ShopRead.model_validate(data)
    return api_response(200, "Shop Created Successfully", read)


@router.get(
    "/read/{id_slug}",
    description="Shop ID (int) or slug (str)",
    response_model=ShopRead,
)
def get(id_slug: str, session: GetSession):
    # Check if it's an integer ID
    if id_slug.isdigit():
        read = session.get(Shop, int(id_slug))
    else:
        # Otherwise treat as slug
        read = session.exec(select(Shop).where(Shop.slug.ilike(id_slug))).first()
    raiseExceptions((read, 404, "Shop not found"))

    return api_response(200, "Shop Found", ShopRead.model_validate(read))


# ✅ UPDATE shop
@router.put("/update/{id}")
@handle_async_wrapper
def update_shop(
    id: int,
    request: ShopUpdate,
    session: GetSession,
    user=requirePermission(["shop_admin","shop:update"]),
):
    shop = session.get(Shop, id)
    raiseExceptions((shop, 404, "Shop not found"))
    if user.get("id") != shop.owner_id:
        return api_response(403, "You are not the owner of this shop")
    data = updateOp(shop, request, session)
    if data.name:
        data.slug = uniqueSlugify(session, Shop, data.name)

    session.add(data)
    session.commit()
    session.refresh(data)
    return api_response(200, "Shop Updated Successfully", ShopRead.model_validate(data))


# ✅ UPDATE shop Status
@router.put("/shop_status_update/{shop_id}")
def update_shop(
    shop_id: int,
    request: ShopVerifyByAdmin,
    session: GetSession,
    user=requirePermission(["approve:approve","shop:reject","shop:deactivate","shop:activate"]),
):
    db_shop = session.get(Shop, shop_id)  # Like findById
    raiseExceptions((db_shop, 404, "Shop not found"))

    # Track previous status for notification
    was_active = db_shop.is_active

    verify = updateOp(db_shop, request, session)

    session.commit()
    session.refresh(db_shop)

    # Send notifications based on status change
    if db_shop.is_active and not was_active:
        # Shop was approved
        NotificationHelper.notify_shop_approved(
            session=session,
            shop_id=db_shop.id
        )
    elif not db_shop.is_active and was_active:
        # Shop was disapproved
        NotificationHelper.notify_shop_disapproved(
            session=session,
            shop_id=db_shop.id,
            reason="Shop status changed by admin"
        )

    return api_response(200, "Shop Status Updated", ShopRead.model_validate(db_shop))


# ✅ DELETE shop
@router.delete("/delete/{id}")
def delete_shop(id: int, session: GetSession, user=requirePermission(["shop_admin","shop:delete"])):
    shop = session.get(Shop, id)
    raiseExceptions((shop, 404, "Shop not found"))

    session.delete(shop)
    session.commit()
    return api_response(200, "Shop Deleted Successfully")


# ✅ LIST shops (reusable listRecords)
@router.get("/list", response_model=list[ShopReadWithEarnings])
def list_shops(
    session: GetSession,
    query_params: ListQueryParams,
    user=requirePermission(["shop:*","vendor:view"]),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    owner_id: Optional[int] = Query(None, description="Filter by owner ID"),
    has_products: Optional[bool] = Query(None, description="Filter shops with/without products"),
    has_orders: Optional[bool] = Query(None, description="Filter shops with/without orders"),
    min_balance: Optional[Decimal] = Query(None, description="Minimum available balance"),
    max_balance: Optional[Decimal] = Query(None, description="Maximum available balance"),
):
    query_params_dict = vars(query_params)
    page = int(query_params_dict.get("page", 1))
    skip = int(query_params_dict.get("skip", 0))
    limit = int(query_params_dict.get("limit", 10))
    sort = query_params_dict.get("sort")
    print(f"DEBUG: sort param = {sort}, type = {type(sort)}")

    # Build base query
    statement = select(Shop)
    
    if is_active is not None:
        statement = statement.where(Shop.is_active == is_active)

    if owner_id is not None:
        statement = statement.where(Shop.owner_id == owner_id)

    # Apply search if provided
    search_term = query_params_dict.get("searchTerm")
    if search_term:
        search_pattern = f"%{search_term}%"
        statement = statement.where(
            or_(
                Shop.name.ilike(search_pattern),
                Shop.slug.ilike(search_pattern),
                Shop.description.ilike(search_pattern),
            )
        )

    # Process each shop to add extra fields
    shops_with_extra = []
    dynamic_sort = None  # Store dynamic sort for after data is fetched
    
    # Check if sort is for dynamic fields (needs to be applied after fetching data)
    if sort:
        import ast
        try:
            # Handle both formats: ["created_at","desc"] or ['created_at','desc']
            if isinstance(sort, str):
                # Replace single quotes with double quotes for JSON parsing
                sort_str = sort.replace("'", '"').replace("%27", '"')
                try:
                    sort_list = ast.literal_eval(sort_str)
                except:
                    sort_list = ast.literal_eval(sort)
            else:
                sort_list = sort
            
            # Check if it's a nested list (multiple sorts) or single sort
            if sort_list and isinstance(sort_list[0], list):
                # Multiple sorts: [['created_at','desc'], ['name','asc']]
                for s in sort_list:
                    if len(s) >= 2:
                        sort_col, sort_dir = s[0], s[1]
                        if sort_col in ("available_balance", "total_orders", "total_products"):
                            dynamic_sort = (sort_col, sort_dir)
                        else:
                            statement = _apply_sort(statement, sort_col, sort_dir)
            else:
                # Single sort: ['created_at','desc']
                if len(sort_list) >= 2:
                    sort_col, sort_dir = sort_list[0], sort_list[1]
                    if sort_col in ("available_balance", "total_orders", "total_products"):
                        dynamic_sort = (sort_col, sort_dir)
                    else:
                        statement = _apply_sort(statement, sort_col, sort_dir)
        except Exception as e:
            print(f"Sort error: {e}")
            pass

    # Get total count before pagination and filters
    total_count = len(session.exec(statement).all())

    # Execute query WITHOUT pagination first to apply filters
    shops = session.exec(statement).all()

    for shop in shops:
        # Get earnings summary
        earnings_stmt = select(
            func.coalesce(func.sum(ShopEarning.shop_earning), 0),
            func.coalesce(func.sum(ShopEarning.settled_amount), 0),
        ).where(ShopEarning.shop_id == shop.id)
        earnings_result = session.exec(earnings_stmt).first()
        total_earnings = Decimal("0.00")
        total_settled = Decimal("0.00")
        if earnings_result:
            total_earnings = Decimal(str(earnings_result[0])) if earnings_result[0] else Decimal("0.00")
            total_settled = Decimal(str(earnings_result[1])) if earnings_result[1] else Decimal("0.00")
        available_balance = total_earnings - total_settled

        # Get product count
        products_stmt = select(func.count(Product.id)).where(Product.shop_id == shop.id)
        total_products = session.exec(products_stmt).first() or 0

        # Get orders count (unique orders) - try with int conversion
        try:
            orders_stmt = select(func.count(func.distinct(OrderProduct.order_id))).where(
                OrderProduct.shop_id == shop.id
            )
            result = session.exec(orders_stmt).first()
            total_orders = int(result) if result is not None else 0
            print(f"DEBUG: Shop {shop.id} - total_orders: {total_orders}, result type: {type(result)}, result value: {result}")
        except Exception as e:
            print(f"ERROR: Shop {shop.id} - {e}")
            total_orders = 0

        # Get products in cart
        from src.api.models.cart_model.cartModel import Cart
        cart_stmt = select(func.count(func.distinct(Cart.product_id))).where(Cart.shop_id == shop.id)
        products_in_cart = session.exec(cart_stmt).first() or 0

        # Get products in orders
        products_in_orders_stmt = select(func.count(func.distinct(OrderProduct.product_id))).where(OrderProduct.shop_id == shop.id)
        products_in_orders = session.exec(products_in_orders_stmt).first() or 0

        # Apply filters
        if has_products is not None:
            if has_products and total_products == 0:
                continue
            if not has_products and total_products > 0:
                continue

        if has_orders is not None:
            if has_orders and total_orders == 0:
                continue
            if not has_orders and total_orders > 0:
                continue

        if min_balance is not None and available_balance is not None and available_balance < min_balance:
            continue

        if max_balance is not None and available_balance is not None and available_balance > max_balance:
            continue

        # Explicitly set all fields including total_orders
        shop_data = ShopReadWithEarnings.model_validate(shop)
        shop_data.total_earnings = total_earnings
        shop_data.total_settled = total_settled
        shop_data.available_balance = available_balance
        shop_data.total_products = total_products
        shop_data.total_orders = total_orders  # Explicitly set
        shop_data.has_products = total_products > 0
        shop_data.has_orders = total_orders > 0
        shop_data.products_in_cart = products_in_cart
        shop_data.products_in_orders = products_in_orders
        
        print(f"DEBUG: Setting shop {shop.id} -> total_orders={total_orders}, has_orders={total_orders > 0}")
        
        shops_with_extra.append(shop_data)

    # Apply dynamic sorting (for available_balance, total_orders, total_products)
    if dynamic_sort:
        print(f"Applying dynamic sort: {dynamic_sort}")
        sort_col, sort_dir = dynamic_sort
        reverse = sort_dir == "desc"
        
        if sort_col == "available_balance":
            shops_with_extra.sort(key=lambda x: float(x.available_balance or 0), reverse=reverse)
        elif sort_col == "total_orders":
            shops_with_extra.sort(key=lambda x: x.total_orders or 0, reverse=reverse)
        elif sort_col == "total_products":
            shops_with_extra.sort(key=lambda x: x.total_products or 0, reverse=reverse)
    else:
        print(f"No dynamic sort set, sort param was: {sort}")

    # Total count AFTER filters but BEFORE pagination
    filtered_total = len(shops_with_extra)

    # Apply pagination AFTER filters
    paginated_results = shops_with_extra[skip:skip + limit]

    return api_response(200, f"Found {len(paginated_results)} shop(s)", paginated_results, filtered_total)


def _apply_sort(statement, sort_col, sort_dir):
    if hasattr(Shop, sort_col):
        order_attr = getattr(Shop, sort_col)
        if sort_dir == "desc":
            return statement.order_by(desc(order_attr))
        else:
            return statement.order_by(asc(order_attr))
    return statement


# ✅ LIST shops for signed-in user with earnings summary
@router.get("/my-shops")
def my_shops(
    session: GetSession,
    user: requireSignin,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    has_products: Optional[bool] = Query(None, description="Filter shops with/without products"),
    has_orders: Optional[bool] = Query(None, description="Filter shops with/without orders"),
    min_balance: Optional[Decimal] = Query(None, description="Minimum available balance"),
    max_balance: Optional[Decimal] = Query(None, description="Maximum available balance"),
):
    """Get all shops owned by signed-in user with earnings summary"""
    user_id = user.get("id")

    # Build query for user's shops
    query = select(Shop).where(Shop.owner_id == user_id)
    if is_active is not None:
        query = query.where(Shop.is_active == is_active)

    shops = session.exec(query).all()

    if not shops:
        return api_response(200, "No shops found", [], 0)

    # Build response with earnings data for each shop
    shops_with_earnings = []
    for shop in shops:
        # Get earnings summary for this shop
        earnings_stmt = select(
            func.coalesce(func.sum(ShopEarning.shop_earning), 0),
            func.coalesce(func.sum(ShopEarning.settled_amount), 0),
        ).where(ShopEarning.shop_id == shop.id)

        earnings_result = session.exec(earnings_stmt).first()
        total_earnings = Decimal(str(earnings_result[0])) if earnings_result[0] else Decimal("0.00")
        total_settled = Decimal(str(earnings_result[1])) if earnings_result[1] else Decimal("0.00")
        
        available_balance = total_earnings - total_settled

        # Get total products
        products_stmt = select(func.count(Product.id)).where(Product.shop_id == shop.id)
        total_products = session.exec(products_stmt).first() or 0

        # Get total active and inactive products
        active_products_stmt = select(func.count(Product.id)).where(
            Product.shop_id == shop.id, Product.status == "publish", Product.is_active == True
        )
        total_active_products = session.exec(active_products_stmt).first() or 0

        inactive_products_stmt = select(func.count(Product.id)).where(
            Product.shop_id == shop.id, or_(Product.status != "publish", Product.is_active == False)
        )
        total_inactive_products = session.exec(inactive_products_stmt).first() or 0

        # Get total orders
        orders_stmt = select(func.count(func.distinct(OrderProduct.order_id))).where(
            OrderProduct.shop_id == shop.id,
            OrderProduct.shop_id.isnot(None)
        )
        total_orders = session.exec(orders_stmt).first() or 0

        # Get products in cart
        from src.api.models.cart_model.cartModel import Cart
        cart_stmt = select(func.count(func.distinct(Cart.product_id))).where(Cart.shop_id == shop.id)
        products_in_cart = session.exec(cart_stmt).first() or 0

        # Get products in orders
        products_in_orders_stmt = select(func.count(func.distinct(OrderProduct.product_id))).where(
            OrderProduct.shop_id == shop.id,
            OrderProduct.shop_id.isnot(None)
        )
        products_in_orders = session.exec(products_in_orders_stmt).first() or 0

        # Apply filters
        if has_products is not None:
            if has_products and total_products == 0:
                continue
            if not has_products and total_products > 0:
                continue

        if has_orders is not None:
            if has_orders and total_orders == 0:
                continue
            if not has_orders and total_orders > 0:
                continue

        if min_balance is not None and available_balance < min_balance:
            continue

        if max_balance is not None and available_balance > max_balance:
            continue

        # Create shop response with earnings
        shop_data = ShopReadWithEarnings.model_validate(shop)
        shop_data.total_earnings = total_earnings
        shop_data.total_settled = total_settled
        shop_data.available_balance = available_balance
        shop_data.total_active_products = total_active_products
        shop_data.total_inactive_products = total_inactive_products
        shop_data.total_orders = total_orders
        shop_data.has_products = total_products > 0
        shop_data.has_orders = total_orders > 0
        shop_data.products_in_cart = products_in_cart
        shop_data.products_in_orders = products_in_orders

        shops_with_earnings.append(shop_data)

    return api_response(
        200,
        f"Found {len(shops_with_earnings)} shop(s)",
        shops_with_earnings,
        len(shops_with_earnings)
    )
# ✅ PATCH shop status (toggle/verify)
@router.patch("/{id}/status")
def patch_shop_status(
    id: int,
    request: ShopVerifyByAdmin,
    session: GetSession,
    user=requirePermission(["shop:approve", "shop:toggle","shop:reject","shop:activate","shop:deactivate"]),  # 🔒 both allowed
):
    shop = session.get(Shop, id)
    raiseExceptions((shop, 404, "Shop not found"))

    # only update status fields
    updated = updateOp(shop, request, session)

    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Shop status updated successfully", ShopRead.model_validate(updated))
@router.get("/read-with-earnings/{id_slug}", response_model=ShopReadWithEarnings)
def get_shop_with_earnings(
    id_slug: str, 
    session: GetSession,
    user: requireSignin  # Optional: if you want to restrict to owners/admins
):
    # Check if it's an integer ID
    if id_slug.isdigit():
        shop = session.get(Shop, int(id_slug))
    else:
        # Otherwise treat as slug
        shop = session.exec(select(Shop).where(Shop.slug.ilike(id_slug))).first()
    
    raiseExceptions((shop, 404, "Shop not found"))
    
    # Get earnings summary for this shop
    earnings_stmt = select(
        func.coalesce(func.sum(ShopEarning.shop_earning), 0),
        func.coalesce(func.sum(ShopEarning.settled_amount), 0),
        func.coalesce(func.sum(ShopEarning.admin_commission), 0)
    ).where(ShopEarning.shop_id == shop.id)

    earnings_result = session.exec(earnings_stmt).first()
    total_earnings = Decimal(str(earnings_result[0])) if earnings_result[0] else Decimal("0.00")
    total_settled = Decimal(str(earnings_result[1])) if earnings_result[1] else Decimal("0.00")
    
    # Get total admin commission using OrderProduct
    admin_comm_stmt = select(func.coalesce(func.sum(OrderProduct.admin_commission), 0)).where(OrderProduct.shop_id == shop.id)
    admin_comm_result = session.exec(admin_comm_stmt).first()
    total_admin_commission = Decimal(str(admin_comm_result)) if admin_comm_result else Decimal("0.00")
    
    available_balance = total_earnings - total_settled

    # Get total active and inactive products
    active_products_stmt = select(func.count(Product.id)).where(
        Product.shop_id == shop.id, Product.status == "publish", Product.is_active == True
    )
    total_active_products = session.exec(active_products_stmt).first() or 0

    inactive_products_stmt = select(func.count(Product.id)).where(
        Product.shop_id == shop.id, or_(Product.status != "publish", Product.is_active == False)
    )
    total_inactive_products = session.exec(inactive_products_stmt).first() or 0

    # Get total orders
    orders_stmt = select(func.count(func.distinct(OrderProduct.order_id))).where(
        OrderProduct.shop_id == shop.id,
        OrderProduct.shop_id.isnot(None)
    )
    total_orders = session.exec(orders_stmt).first() or 0

    # Create shop response with earnings
    shop_data = ShopReadWithEarnings.model_validate(shop)
    shop_data.total_earnings = total_earnings
    shop_data.total_settled = total_settled
    shop_data.total_admin_commission = total_admin_commission
    shop_data.available_balance = available_balance
    shop_data.total_active_products = total_active_products
    shop_data.total_inactive_products = total_inactive_products
    shop_data.total_orders = total_orders

    return api_response(200, "Shop found with earnings", shop_data)