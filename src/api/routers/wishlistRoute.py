# src/api/routes/wishlistRoute.py
from fastapi import APIRouter
from sqlalchemy import select
from typing import Optional
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)
from src.api.models.product_model.wishlistsModel import Wishlist, WishlistCreate, WishlistUpdate, WishlistRead

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


# ✅ ADD TO WISHLIST
@router.post("/add")
def add_to_wishlist(
    request: WishlistCreate,
    session: GetSession,
    user=requireSignin,
):
    print("❤️ Adding to wishlist:", request.model_dump())

    # Check if item already exists in wishlist
    existing_item = session.exec(
        select(Wishlist).where(
            Wishlist.user_id == request.user_id,
            Wishlist.product_id == request.product_id,
            Wishlist.variation_option_id == request.variation_option_id
        )
    ).first()
    
    if existing_item:
        return api_response(400, "Item already exists in wishlist")

    wishlist_item = Wishlist(**request.model_dump())
    session.add(wishlist_item)
    session.commit()
    session.refresh(wishlist_item)

    return api_response(201, "Item added to wishlist successfully", WishlistRead.model_validate(wishlist_item))


# ✅ UPDATE WISHLIST ITEM
@router.put("/update/{id}")
def update_wishlist_item(
    id: int,
    request: WishlistUpdate,
    session: GetSession,
    user=requireSignin,
):
    wishlist_item = session.get(Wishlist, id)
    raiseExceptions((wishlist_item, 404, "Wishlist item not found"))

    # Check if user owns this wishlist item
    if wishlist_item.user_id != user.id:  # Assuming user object has id
        return api_response(403, "Not authorized to update this wishlist item")

    updated = updateOp(wishlist_item, request, session)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Wishlist item updated successfully", WishlistRead.model_validate(updated))


# ✅ GET WISHLIST ITEM BY ID
@router.get("/read/{id}")
def read_wishlist_item(id: int, session: GetSession, user=requireSignin):
    wishlist_item = session.get(Wishlist, id)
    raiseExceptions((wishlist_item, 404, "Wishlist item not found"))

    # Check if user owns this wishlist item
    if wishlist_item.user_id != user.id:
        return api_response(403, "Not authorized to view this wishlist item")

    return api_response(200, "Wishlist item found", WishlistRead.model_validate(wishlist_item))


# ✅ REMOVE FROM WISHLIST
@router.delete("/remove/{id}")
def remove_from_wishlist(
    id: int,
    session: GetSession,
    user=requireSignin,
):
    wishlist_item = session.get(Wishlist, id)
    raiseExceptions((wishlist_item, 404, "Wishlist item not found"))

    # Check if user owns this wishlist item
    if wishlist_item.user_id != user.id:
        return api_response(403, "Not authorized to remove this wishlist item")

    session.delete(wishlist_item)
    session.commit()
    return api_response(200, f"Item removed from wishlist successfully")


# ✅ REMOVE FROM WISHLIST BY PRODUCT
@router.delete("/remove-by-product")
def remove_from_wishlist_by_product(
    product_id: int,
    session: GetSession,
    user=requireSignin,
    variation_option_id: Optional[int] = None,
):
    # Find the wishlist item
    query = select(Wishlist).where(
        Wishlist.user_id == user.id,
        Wishlist.product_id == product_id
    )
    
    if variation_option_id is not None:
        query = query.where(Wishlist.variation_option_id == variation_option_id)
    else:
        query = query.where(Wishlist.variation_option_id.is_(None))

    wishlist_item = session.exec(query).first()
    
    if not wishlist_item:
        return api_response(404, "Wishlist item not found")

    session.delete(wishlist_item)
    session.commit()
    return api_response(200, "Item removed from wishlist successfully")


# ✅ LIST USER'S WISHLIST
@router.get("/my-wishlist", response_model=list[WishlistRead])
def list_my_wishlist(
    query_params: ListQueryParams,
    session: GetSession,
    user=requireSignin
):
    query_params = vars(query_params)
    
    # Filter by current user
    if "filters" not in query_params:
        query_params["filters"] = {}
    query_params["filters"]["user_id"] = user.id
    
    return listRecords(
        query_params=query_params,
        searchFields=[],  # No search fields for wishlist
        Model=Wishlist,
        Schema=WishlistRead,
    )


# ✅ LIST ALL WISHLISTS (Admin only)
@router.get("/list", response_model=list[WishlistRead])
def list_all_wishlists(
    query_params: ListQueryParams,
    user=requirePermission("wishlist:view_all")
):
    query_params = vars(query_params)
    
    return listRecords(
        query_params=query_params,
        searchFields=[],
        Model=Wishlist,
        Schema=WishlistRead,
    )


# ✅ CHECK IF PRODUCT IS IN WISHLIST
@router.get("/check/{product_id}")
def check_in_wishlist(
    product_id: int,
    session: GetSession,
    user=requireSignin,
    variation_option_id: Optional[int] = None,
):
    query = select(Wishlist).where(
        Wishlist.user_id == user.id,
        Wishlist.product_id == product_id
    )
    
    if variation_option_id is not None:
        query = query.where(Wishlist.variation_option_id == variation_option_id)
    else:
        query = query.where(Wishlist.variation_option_id.is_(None))

    wishlist_item = session.exec(query).first()
    
    if wishlist_item:
        return api_response(200, "Product is in wishlist", {
            "in_wishlist": True,
            "wishlist_item": WishlistRead.model_validate(wishlist_item)
        })
    else:
        return api_response(200, "Product is not in wishlist", {
            "in_wishlist": False
        })


# ✅ GET WISHLIST BY USER ID (Admin or same user)
@router.get("/user/{user_id}", response_model=list[WishlistRead])
def get_wishlist_by_user(
    user_id: int,
    query_params: ListQueryParams,
    session: GetSession,
    user=requireSignin
):
    # Allow users to view their own wishlist or admin to view any
    if user_id != user.id and not user.has_permission("wishlist:view_all"):
        return api_response(403, "Not authorized to view this user's wishlist")

    query_params = vars(query_params)
    
    # Add user filter
    if "filters" not in query_params:
        query_params["filters"] = {}
    query_params["filters"]["user_id"] = user_id
    
    return listRecords(
        query_params=query_params,
        searchFields=[],
        Model=Wishlist,
        Schema=WishlistRead,
    )