from typing import List
from fastapi import APIRouter, Body, HTTPException
from sqlalchemy import select
from sqlmodel import col
from src.api.core.utility import Print
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.cart_model import Cart, CartCreate, CartRead, CartUpdate, CartBulkCreate, CartBulkResponse
from src.api.core.dependencies import GetSession, ListQueryParams, requireSignin


router = APIRouter(prefix="/cart", tags=["Cart"])


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
):
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
    user: requireSignin,
    product_ids: List[int] = Body(
        ..., embed=True, description="List of product IDs to delete"
    ),
    session: GetSession = None,
):
    """
    Delete multiple cart items by product IDs for the logged-in user
    Example request body:
    {
        "product_ids": [1, 2, 3]
    }
    """
    stmt = select(Cart).where(
        Cart.user_id == user["id"],
        Cart.product_id.in_(product_ids)
    )
    carts = session.execute(stmt).scalars().all()

    raiseExceptions((carts, 404, "No matching cart items found"))

    for cart in carts:
        session.delete(cart)
    session.commit()

    return api_response(200, f"{len(carts)} cart items deleted successfully")


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