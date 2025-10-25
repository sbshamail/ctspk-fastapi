from typing import List
from fastapi import APIRouter, Body
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

    cart = Cart(**request.model_dump())
    cart.user_id = user.get("id")
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
            {"product_id": 1, "shop_id": 1, "quantity": 2},
            {"product_id": 2, "shop_id": 1, "quantity": 1},
            {"product_id": 3, "shop_id": 2, "quantity": 3}
        ]
    }
    """
    user_id = user["id"]
    success_count = 0
    failed_count = 0
    failed_items = []

    for item in request.items:
        try:
            # Check if item already exists in cart
            existing_cart = session.exec(
                select(Cart)
                .where(Cart.user_id == user_id)
                .where(Cart.product_id == item.product_id)
            ).first()

            if existing_cart:
                # Update quantity if item exists
                existing_cart.quantity += item.quantity
                success_count += 1
            else:
                # Create new cart item
                cart_item = Cart(
                    **item.model_dump(),
                    user_id=user_id
                )
                session.add(cart_item)
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
        
        # Refresh successful items to get their IDs
        if success_count > 0:
            session.flush()
        
        message = f"Successfully processed {success_count} items"
        if failed_count > 0:
            message += f", {failed_count} items failed"

        return CartBulkResponse(
            success_count=success_count,
            failed_count=failed_count,
            failed_items=failed_items,
            message=message
        )

    except Exception as e:
        session.rollback()
        return CartBulkResponse(
            success_count=0,
            failed_count=len(request.items),
            failed_items=[{"error": f"Database error: {str(e)}"} for _ in request.items],
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
    cart = (
        session.exec(
            select(Cart)
            .where(Cart.product_id == product_id)
            .where(Cart.user_id == user["id"])
        )
        .scalars()
        .first()
    )

    raiseExceptions((cart, 404, "Cart not found"))

    updateOp(cart, request, session)

    # Ensure min quantity = 1
    if request.quantity is not None and request.quantity < 1:
        request.quantity = 1
    session.commit()
    session.refresh(cart)
    return api_response(200, "Cart Update Successfully", CartRead.model_validate(cart))


@router.get("/read/{product_id}")
def get_role(product_id: int, session: GetSession, user: requireSignin):
    cart = (
        session.exec(
            select(Cart)
            .where(Cart.product_id == product_id)
            .where(Cart.user_id == user["id"])
        )
        .scalars()
        .first()
    )
    raiseExceptions((cart, 400, "Cart not found"))

    return api_response(200, "Cart Found", CartRead.model_validate(cart))


# ❗ DELETE
@router.delete("/delete/{product_id}", response_model=dict)
def delete_role(
    product_id: int,
    session: GetSession,
    user: requireSignin,
):
    cart = (
        session.exec(
            select(Cart)
            .where(Cart.product_id == product_id)
            .where(Cart.user_id == user["id"])
        )
        .scalars()
        .first()
    )
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
    carts = (
        session.exec(
            select(Cart)
            .where(Cart.user_id == user["id"])
            .where(Cart.product_id.in_(product_ids))
        )
        .scalars()
        .all()
    )

    raiseExceptions((carts, 404, "No matching cart items found"))

    for c in carts:
        session.delete(c)
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
    carts = session.exec(select(Cart).where(Cart.user_id == user["id"])).scalars().all()

    raiseExceptions((carts, 404, "No cart items found"))

    for c in carts:
        session.delete(c)
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