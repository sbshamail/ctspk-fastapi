from typing import List, Optional
from fastapi import APIRouter, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlmodel import col
from src.api.core.utility import Print
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.cart_model import (
    Cart, CartCreate, CartRead, CartUpdate, CartBulkCreate, CartBulkResponse,
    CartBase, CartItemResponse, MyCartResponse, AddCartResponse,
    BulkAddCartRequest, BulkAddCartResponse, CartQuantityUpdate, CartDeleteRequest,
    CartDeleteManyRequest
)
from src.api.models.product_model.productsModel import Product
from src.api.models.product_model.variationOptionModel import VariationOption
from src.api.core.dependencies import GetSession, ListQueryParams, requireSignin


router = APIRouter(prefix="/cart", tags=["Cart"])


def build_cart_item_response(
    cart: Cart,
    product: Product,
    variation_option: Optional[VariationOption] = None
) -> CartItemResponse:
    """Helper function to build CartItemResponse from cart, product, and optionally variation_option"""

    # Get image URL from product or variation
    image_url = None
    if variation_option and variation_option.image:
        image_url = variation_option.image.get("original") or variation_option.image.get("thumbnail")
    elif product.image:
        image_url = product.image.get("original") or product.image.get("thumbnail")

    # Determine prices based on whether variation exists
    if variation_option:
        # Use variation prices
        unit_price = float(variation_option.sale_price) if variation_option.sale_price else float(variation_option.price)
        original_price = float(variation_option.price)
    else:
        # Use product prices
        unit_price = product.sale_price if product.sale_price else product.price
        original_price = product.price

    # Calculate discount
    discount = original_price - unit_price if original_price > unit_price else 0

    # Get title - use variation title if exists, otherwise product name
    title = variation_option.title if variation_option else product.name

    return CartItemResponse(
        product_id=cart.product_id,
        shop_id=cart.shop_id,
        quantity=cart.quantity,
        variation_option_id=cart.variation_option_id,
        title=title,
        unit_price=unit_price,
        original_price=original_price,
        discount=discount,
        imageUrl=image_url,
        unit=product.unit
    )


@router.get("/my-cart", response_model=MyCartResponse)
def get_my_cart(
    session: GetSession,
    user: requireSignin,
):
    """
    Get all cart items for the logged-in user with product details
    """
    user_id = user.get("id")

    # Get all cart items for this user with product relationship
    stmt = select(Cart).where(Cart.user_id == user_id).options(joinedload(Cart.product))
    cart_items = session.execute(stmt).scalars().unique().all()

    cart_responses = []
    for cart in cart_items:
        product = cart.product
        if not product:
            continue

        # Get variation option if exists
        variation_option = None
        if cart.variation_option_id:
            var_stmt = select(VariationOption).where(VariationOption.id == cart.variation_option_id)
            variation_option = session.execute(var_stmt).scalar_one_or_none()

        cart_response = build_cart_item_response(cart, product, variation_option)
        cart_responses.append(cart_response)

    return MyCartResponse(success=1, data=cart_responses)


@router.post("/add", response_model=AddCartResponse)
def add_to_cart(
    request: CartBase,
    session: GetSession,
    user: requireSignin,
):
    """
    Add a single item to cart
    Request body: {"product_id": 0, "shop_id": 0, "quantity": 0, "variation_option_id": null or value}
    """
    user_id = user.get("id")

    # Check if cart item already exists for this user and product
    stmt = select(Cart).where(
        Cart.user_id == user_id,
        Cart.product_id == request.product_id
    )
    existing_cart = session.execute(stmt).scalar_one_or_none()

    if existing_cart:
        # Update quantity if item exists
        existing_cart.quantity += request.quantity
        if request.variation_option_id is not None:
            existing_cart.variation_option_id = request.variation_option_id
        session.add(existing_cart)
        session.commit()
        session.refresh(existing_cart)
        cart = existing_cart
    else:
        # Create new cart item
        cart_data = request.model_dump()
        cart = Cart(**cart_data)
        cart.user_id = user_id
        session.add(cart)
        session.commit()
        session.refresh(cart)

    # Get product details
    product_stmt = select(Product).where(Product.id == cart.product_id)
    product = session.execute(product_stmt).scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get variation option if exists
    variation_option = None
    if cart.variation_option_id:
        var_stmt = select(VariationOption).where(VariationOption.id == cart.variation_option_id)
        variation_option = session.execute(var_stmt).scalar_one_or_none()

    cart_response = build_cart_item_response(cart, product, variation_option)
    return AddCartResponse(success=1, data=cart_response)


@router.post("/bulk-add", response_model=BulkAddCartResponse)
def bulk_add_to_cart(
    request: BulkAddCartRequest,
    session: GetSession,
    user: requireSignin,
):
    """
    Bulk add multiple items to cart
    Request body: {"items": [{"product_id": 0, "shop_id": 0, "quantity": 0, "variation_option_id": null or value}]}
    """
    user_id = user.get("id")

    # Get all existing cart items for this user
    stmt = select(Cart).where(Cart.user_id == user_id)
    existing_carts = session.execute(stmt).scalars().all()
    existing_cart_dict = {cart.product_id: cart for cart in existing_carts}

    added_carts = []

    for item in request.items:
        if item.product_id in existing_cart_dict:
            # Update quantity if item exists
            existing_cart = existing_cart_dict[item.product_id]
            existing_cart.quantity += item.quantity
            if item.variation_option_id is not None:
                existing_cart.variation_option_id = item.variation_option_id
            session.add(existing_cart)
            added_carts.append(existing_cart)
        else:
            # Create new cart item
            cart_data = {
                "product_id": item.product_id,
                "shop_id": item.shop_id,
                "quantity": item.quantity,
                "variation_option_id": item.variation_option_id,
                "user_id": user_id
            }
            cart = Cart(**cart_data)
            session.add(cart)
            existing_cart_dict[item.product_id] = cart
            added_carts.append(cart)

    session.commit()

    # Refresh all carts to get their IDs
    for cart in added_carts:
        session.refresh(cart)

    # Build response for all added items
    cart_responses = []
    for cart in added_carts:
        # Get product details
        product_stmt = select(Product).where(Product.id == cart.product_id)
        product = session.execute(product_stmt).scalar_one_or_none()

        if not product:
            continue

        # Get variation option if exists
        variation_option = None
        if cart.variation_option_id:
            var_stmt = select(VariationOption).where(VariationOption.id == cart.variation_option_id)
            variation_option = session.execute(var_stmt).scalar_one_or_none()

        cart_response = build_cart_item_response(cart, product, variation_option)
        cart_responses.append(cart_response)

    return BulkAddCartResponse(success=1, data=cart_responses)


@router.post("/create")
def create_role(
    request: CartCreate,
    session: GetSession,
    user: requireSignin,
):
    user_id = user.get("id")
    
    # Check if cart item already exists for this user and product
    stmt = select(Cart).where(
        Cart.user_id == user_id,
        Cart.product_id == request.product_id
    )
    existing_cart = session.execute(stmt).scalar_one_or_none()

    if existing_cart:
        # Update quantity if item exists
        existing_cart.quantity += request.quantity
        session.add(existing_cart)
        session.commit()
        session.refresh(existing_cart)
        return api_response(200, "Cart quantity updated", CartRead.model_validate(existing_cart))
    else:
        # Create new cart item - handle variation_option_id properly
        cart_data = request.model_dump()
        # If variation_option_id is not provided, set it to None explicitly
        if cart_data.get('variation_option_id') is None:
            cart_data['variation_option_id'] = None
            
        cart = Cart(**cart_data)
        cart.user_id = user_id
        session.add(cart)
        session.commit()
        session.refresh(cart)
        return api_response(200, "Cart Created Successfully", CartRead.model_validate(cart))


@router.post("/bulk-create", response_model=CartBulkResponse)
def bulk_create_cart_items(
    request: CartBulkCreate,
    session: GetSession,
    user: requireSignin,
):
    """
    Bulk insert multiple cart items for the logged-in user
    Example request body:
    {
        "items": [
            {"product_id": 1, "shop_id": 1, "quantity": 2, "variation_option_id": 1},
            {"product_id": 2, "shop_id": 1, "quantity": 1},
            {"product_id": 3, "shop_id": 2, "quantity": 3, "variation_option_id": 2}
        ]
    }
    """
    user_id = user["id"]
    success_count = 0
    failed_count = 0
    failed_items = []

    # Get all existing cart items for this user to check for duplicates
    stmt = select(Cart).where(Cart.user_id == user_id)
    existing_carts = session.execute(stmt).scalars().all()
    
    existing_cart_dict = {cart.product_id: cart for cart in existing_carts}

    for item in request.items:
        try:
            if item.product_id in existing_cart_dict:
                # Update quantity if item exists
                existing_cart = existing_cart_dict[item.product_id]
                existing_cart.quantity += item.quantity
                session.add(existing_cart)
                success_count += 1
            else:
                # Create new cart item - handle variation_option_id properly
                cart_data = {
                    "product_id": item.product_id,
                    "shop_id": item.shop_id,
                    "quantity": item.quantity,
                    "variation_option_id": item.variation_option_id if item.variation_option_id is not None else None,
                    "user_id": user_id
                }
                cart_item = Cart(**cart_data)
                session.add(cart_item)
                # Add to existing dict to prevent duplicates in same request
                existing_cart_dict[item.product_id] = cart_item
                success_count += 1

        except Exception as e:
            failed_count += 1
            failed_items.append({
                "product_id": item.product_id,
                "shop_id": item.shop_id,
                "error": str(e)
            })

    try:
        session.commit()
        
        message = f"Successfully processed {success_count} items"
        if failed_count > 0:
            message += f", {failed_count} items failed"

        return CartBulkResponse(
            success = 1 if success_count > 0 else 0,
            success_count=success_count,
            failed_count=failed_count,
            failed_items=failed_items,
            message=message
        )

    except Exception as e:
        session.rollback()
        # Create detailed failed items list
        detailed_failed_items = []
        for item in request.items:
            detailed_failed_items.append({
                "product_id": item.product_id,
                "shop_id": item.shop_id,
                "error": f"Database error: {str(e)}"
            })
        
        return CartBulkResponse(
            success =  0,
            success_count=0,
            failed_count=len(request.items),
            failed_items=detailed_failed_items,
            message="Failed to process bulk insert due to database error"
        )


@router.put("/update/{product_id}", response_model=CartRead)
def update_role(
    product_id: int,
    request: CartUpdate,
    session: GetSession,
    user: requireSignin,
):
    # ✅ Find cart using product_id + user_id
    stmt = select(Cart).where(
        Cart.product_id == product_id,
        Cart.user_id == user["id"]
    )
    cart = session.execute(stmt).scalar_one_or_none()

    raiseExceptions((cart, 404, "Cart not found"))

    # Update the cart item
    if request.quantity is not None:
        cart.quantity = max(1, request.quantity)  # Ensure min quantity = 1

    session.add(cart)
    session.commit()
    session.refresh(cart)
    return api_response(200, "Cart Update Successfully", CartRead.model_validate(cart))


@router.patch("/updatecart/{product_id}", response_model=AddCartResponse)
def update_cart_quantity(
    product_id: int,
    request: CartQuantityUpdate,
    session: GetSession,
    user: requireSignin,
):
    """
    Update cart item quantity and/or variation_option_id
    Request body: {"quantity": 5, "variation_option_id": null or 456}
    """
    user_id = user.get("id")

    # Find cart using product_id + user_id
    stmt = select(Cart).where(
        Cart.product_id == product_id,
        Cart.user_id == user_id
    )
    cart = session.execute(stmt).scalar_one_or_none()

    raiseExceptions((cart, 404, "Cart not found"))

    # Update quantity
    cart.quantity = request.quantity

    # Update variation_option_id (can be null or a value)
    cart.variation_option_id = request.variation_option_id

    session.add(cart)
    session.commit()
    session.refresh(cart)

    # Get product details
    product_stmt = select(Product).where(Product.id == cart.product_id)
    product = session.execute(product_stmt).scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get variation option if exists
    variation_option = None
    if cart.variation_option_id:
        var_stmt = select(VariationOption).where(VariationOption.id == cart.variation_option_id)
        variation_option = session.execute(var_stmt).scalar_one_or_none()

    cart_response = build_cart_item_response(cart, product, variation_option)
    return AddCartResponse(success=1, data=cart_response)


@router.get("/read/{product_id}")
def get_role(product_id: int, session: GetSession, user: requireSignin):
    stmt = select(Cart).where(
        Cart.product_id == product_id,
        Cart.user_id == user["id"]
    )
    cart = session.execute(stmt).scalar_one_or_none()

    raiseExceptions((cart, 400, "Cart not found"))

    return api_response(200, "Cart Found", CartRead.model_validate(cart))


# ❗ DELETE
@router.delete("/delete/{product_id}", response_model=dict)
def delete_role(
    product_id: int,
    session: GetSession,
    user: requireSignin,
    request: Optional[CartDeleteRequest] = None,
):
    """
    Delete cart item by product_id
    Optional body: {"variation_option_id": null or 456}
    If variation_option_id is provided and > 0, delete cart with both product_id and variation_option_id
    Otherwise, delete based on product_id only
    """
    # Check if variation_option_id is provided and valid
    if request and request.variation_option_id is not None and request.variation_option_id > 0:
        stmt = select(Cart).where(
            Cart.product_id == product_id,
            Cart.user_id == user["id"],
            Cart.variation_option_id == request.variation_option_id
        )
    else:
        stmt = select(Cart).where(
            Cart.product_id == product_id,
            Cart.user_id == user["id"]
        )
    cart = session.execute(stmt).scalar_one_or_none()

    raiseExceptions((cart, 404, "Cart not found"))

    session.delete(cart)
    session.commit()
    return api_response(200, f"Cart {cart.id} deleted")

# ❗ REMOVE
@router.delete("/remove/{product_id}", response_model=dict)
def remove_cart_item(
    product_id: int,
    session: GetSession,
    user: requireSignin,
    request: Optional[CartDeleteRequest] = None,
):
    """
    Remove cart item by product_id
    Optional body: {"variation_option_id": null or 456}
    If variation_option_id is provided and > 0, delete cart with both product_id and variation_option_id
    Otherwise, delete based on product_id only
    """
    # Check if variation_option_id is provided and valid
    if request and request.variation_option_id is not None and request.variation_option_id > 0:
        stmt = select(Cart).where(
            Cart.product_id == product_id,
            Cart.user_id == user["id"],
            Cart.variation_option_id == request.variation_option_id
        )
    else:
        stmt = select(Cart).where(
            Cart.product_id == product_id,
            Cart.user_id == user["id"]
        )
    cart = session.execute(stmt).scalar_one_or_none()

    raiseExceptions((cart, 404, "Cart not found"))

    session.delete(cart)
    session.commit()
    return api_response(200, f"Cart {cart.id} deleted")

@router.delete("/delete-many", response_model=dict)
def delete_many_cart_items(
    request: CartDeleteManyRequest,
    user: requireSignin,
    session: GetSession,
):
    """
    Delete multiple cart items for the logged-in user
    Example request body:
    {
        "items": [
            {"product_id": 1, "variation_option_id": null},
            {"product_id": 2, "variation_option_id": 456},
            {"product_id": 3}
        ]
    }
    If variation_option_id is provided and > 0, delete cart with both product_id and variation_option_id
    Otherwise, delete based on product_id only
    """
    deleted_count = 0

    for item in request.items:
        # Check if variation_option_id is provided and valid
        if item.variation_option_id is not None and item.variation_option_id > 0:
            stmt = select(Cart).where(
                Cart.user_id == user["id"],
                Cart.product_id == item.product_id,
                Cart.variation_option_id == item.variation_option_id
            )
        else:
            stmt = select(Cart).where(
                Cart.user_id == user["id"],
                Cart.product_id == item.product_id
            )

        cart = session.execute(stmt).scalar_one_or_none()
        if cart:
            session.delete(cart)
            deleted_count += 1

    raiseExceptions((deleted_count > 0, 404, "No matching cart items found"))

    session.commit()
    return api_response(200, f"{deleted_count} cart items deleted successfully")


@router.delete("/delete-all", response_model=dict)
def delete_all_cart_items(
    user: requireSignin,
    session: GetSession,
):
    """
    Delete all cart items for the logged-in user
    """
    stmt = select(Cart).where(Cart.user_id == user["id"])
    carts = session.execute(stmt).scalars().all()

    raiseExceptions((carts, 404, "No cart items found"))

    for cart in carts:
        session.delete(cart)
    session.commit()

    return api_response(200, "All cart items deleted successfully")


# ✅ LIST
@router.get("/list", response_model=list[CartRead])
def list(query_params: ListQueryParams, user: requireSignin):
    query_params = vars(query_params)
    searchFields = []
    return listRecords(
        customFilters=[["user_id", user["id"]]],
        query_params=query_params,
        searchFields=searchFields,
        Model=Cart,
        Schema=CartRead,
    )