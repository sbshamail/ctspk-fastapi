from typing import List
from fastapi import APIRouter, Body
from sqlalchemy import select
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.cart_model import Cart, CartCreate, CartRead, CartUpdate
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
    return api_response(200, "Cart Created Successfully", cart)


@router.put("/update/{product_id}", response_model=CartRead)
def update_role(
    product_id: int,
    request: CartUpdate,
    session: GetSession,
    user: requireSignin,
):
    # ✅ Find cart using product_id + user_id
    cart = session.exec(
        select(Cart)
        .where(Cart.product_id == product_id)
        .where(Cart.user_id == user["id"])
    ).first()

    raiseExceptions((cart, 404, "Cart not found"))

    updateOp(cart, request, session)

    # Ensure min quantity = 1
    if request.quantity is not None and request.quantity < 1:
        request.quantity = 1
    session.commit()
    session.refresh(cart)
    return api_response(200, "Cart Update Successfully", cart)


@router.get("/read/{product_id}")
def get_role(product_id: int, session: GetSession, user: requireSignin):

    cart = session.exec(
        select(Cart)
        .where(Cart.product_id == product_id)
        .where(Cart.user_id == user["id"])
    ).first()
    raiseExceptions((cart, 404, "Cart not found"))

    return api_response(200, "Cart Found", cart)


# ❗ DELETE
@router.delete("/delete/{product_id}", response_model=dict)
def delete_role(
    product_id: int,
    session: GetSession,
    user: requireSignin,
):
    cart = session.exec(
        select(Cart)
        .where(Cart.product_id == product_id)
        .where(Cart.user_id == user["id"])
    ).first()
    raiseExceptions((cart, 404, "Cart not found"))

    session.delete(cart)
    session.commit()
    return api_response(404, f"Cart {cart.id} deleted")


@router.delete("/delete-many", response_model=dict)
def delete_many_cart_items(
    product_ids: List[int] = Body(
        ..., embed=True, description="List of product IDs to delete"
    ),
    session: GetSession = None,
    user: dict = requireSignin,
):
    """
    Delete multiple cart items by product IDs for the logged-in user
    Example request body:
    {
        "product_ids": [1, 2, 3]
    }
    """
    carts = session.exec(
        select(Cart)
        .where(Cart.user_id == user["id"])
        .where(Cart.product_id.in_(product_ids))
    ).all()

    raiseExceptions((carts, 404, "No matching cart items found"))

    for c in carts:
        session.delete(c)
    session.commit()

    return api_response(200, f"{len(carts)} cart items deleted successfully")


@router.delete("/delete-all", response_model=dict)
def delete_all_cart_items(
    session: GetSession,
    user: dict = requireSignin,
):
    """
    Delete all cart items for the logged-in user
    """
    carts = session.exec(select(Cart).where(Cart.user_id == user["id"])).all()

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
        query_params=query_params,
        searchFields=searchFields,
        Model=Cart,
        Schema=CartRead,
    )
