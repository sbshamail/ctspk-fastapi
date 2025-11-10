# src/api/routes/wishlistRoute.py
from fastapi import APIRouter
from sqlalchemy import select
from typing import Optional, List
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)
from src.api.models.product_model.wishlistsModel import Wishlist, WishlistCreate, WishlistUpdate, WishlistRead
from src.api.models.product_model.wishlist_schemas import WishlistReadWithProduct, ProductReadForWishlist
from src.api.models.product_model.productsModel import Product

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


# ✅ ADD TO WISHLIST
@router.post("/add")
def add_to_wishlist(
    request: WishlistCreate,
    session: GetSession,
    user:requireSignin,  # This provides the authenticated user
):
    print("❤️ Adding to wishlist:", request.model_dump())
    print(f"👤 Authenticated user ID: {user.get("id")}")

    # Check if item already exists in wishlist
    existing_item = session.exec(
        select(Wishlist).where(
            Wishlist.user_id == user.get("id"),  # Use user.id from requireSignin
            Wishlist.product_id == request.product_id,
            Wishlist.variation_option_id == request.variation_option_id
        )
    ).first()
    
    if existing_item:
        return api_response(400, "Item already exists in wishlist")

    # Create wishlist item with user_id from authenticated user
    wishlist_data = request.model_dump()
    wishlist_data["user_id"] = user.get("id")  # Override with authenticated user ID
    
    wishlist_item = Wishlist(**wishlist_data)
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
    user:requireSignin,
):
    wishlist_item = session.get(Wishlist, id)
    if not wishlist_item:
        return api_response(404, "Wishlist item not found")

    # Check if user owns this wishlist item
    if wishlist_item.user_id != user.get("id"):
        return api_response(403, "Not authorized to update this wishlist item")

    updated = updateOp(wishlist_item, request, session)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Wishlist item updated successfully", WishlistRead.model_validate(updated))


# ✅ GET WISHLIST ITEM BY ID
@router.get("/read/{id}")
def read_wishlist_item(id: int, session: GetSession, user:requireSignin):
    wishlist_item = session.get(Wishlist, id)
    if not wishlist_item:
        return api_response(404, "Wishlist item not found")

    # Check if user owns this wishlist item
    if wishlist_item.user_id != user.get("id"):
        return api_response(403, "Not authorized to view this wishlist item")

    # Get product data
    product = session.get(Product, wishlist_item.product_id)
    if not product:
        return api_response(404, "Product not found")

    # Prepare enhanced response
    enhanced_response = WishlistReadWithProduct(
        id=wishlist_item.id,
        user_id=wishlist_item.user_id,
        product_id=wishlist_item.product_id,
        variation_option_id=wishlist_item.variation_option_id,
        created_at=wishlist_item.created_at,
        product=ProductReadForWishlist(
            id=product.id,
            name=product.name,
            price=product.price,
            sale_price=product.sale_price,
            image=product.image,
            in_stock=product.in_stock,
            slug=product.slug
        )
    )

    return api_response(200, "Wishlist item found", enhanced_response)


# ✅ REMOVE FROM WISHLIST
@router.delete("/remove/{id}")
def remove_from_wishlist(
    id: int,
    session: GetSession,
    user:requireSignin,
):
    wishlist_item = session.get(Wishlist, id)
    if not wishlist_item:
        return api_response(404, "Wishlist item not found")

    # Check if user owns this wishlist item
    if wishlist_item.user_id != user.get("id"):
        return api_response(403, "Not authorized to remove this wishlist item")

    session.delete(wishlist_item)
    session.commit()
    return api_response(200, f"Item removed from wishlist successfully")


# ✅ REMOVE FROM WISHLIST BY PRODUCT
@router.delete("/remove-by-product")
def remove_from_wishlist_by_product(
    product_id: int,
    session: GetSession,
    user:requireSignin,
    variation_option_id: Optional[int] = None,
):
    # Find the wishlist item
    query = select(Wishlist).where(
        Wishlist.user_id == user.get("id"),
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


def get_wishlist_items_with_products(session, query_params, user_id=None):
    """Get wishlist items with product data using direct query"""
    from sqlmodel import select
    
    # Build base query
    query = select(Wishlist)
    
    # Apply filters
    if user_id:
        query = query.where(Wishlist.user_id == user_id)
    
    # Apply pagination
    skip = query_params.get("skip", 0)
    limit = query_params.get("limit", 10)
    query = query.offset(skip).limit(limit)
    
    # Execute query
    wishlist_items = session.exec(query).all()
    
    # Enhance with product data
    enhanced_items = []
    for item in wishlist_items:
        product = session.get(Product, item.product_id)
        if product:
            enhanced_item = WishlistReadWithProduct(
                id=item.id,
                user_id=item.user_id,
                product_id=item.product_id,
                variation_option_id=item.variation_option_id,
                created_at=item.created_at,
                product=ProductReadForWishlist(
                    id=product.id,
                    name=product.name,
                    price=product.price,
                    sale_price=product.sale_price,
                    image=product.image,
                    in_stock=product.in_stock,
                    shop_id=product.shop_id,
                    slug=product.slug
                )
            )
            enhanced_items.append(enhanced_item)
    
    return enhanced_items


def get_wishlist_count(session, user_id=None):
    """Get total count of wishlist items"""
    from sqlmodel import select, func
    
    query = select(func.count(Wishlist.id))
    if user_id:
        query = query.where(Wishlist.user_id == user_id)
    
    return session.exec(query).first()


# ✅ LIST USER'S WISHLIST
@router.get("/my-wishlist")
def list_my_wishlist(
    query_params: ListQueryParams,  
    session: GetSession,  
    user:requireSignin,
):
    query_params_dict = vars(query_params)
    print(f"user:{user}")
    print(f"user_id:{user.get("id")}")
    # Get wishlist items with product data
    enhanced_wishlist = get_wishlist_items_with_products(session, query_params_dict, user.get("id"))
    total_count = get_wishlist_count(session, user.get("id"))
    
    # If no wishlist items found
    if not enhanced_wishlist:
        return api_response(200, "No items in wishlist", [], 0)
    
    return api_response(200, "Wishlist retrieved successfully", enhanced_wishlist, total_count)


# ✅ LIST ALL WISHLISTS (Admin only)
@router.get("/list")
def list_all_wishlists(
    query_params: ListQueryParams,
    session: GetSession,
    user=requirePermission("wishlist:view_all")
):
    query_params_dict = vars(query_params)
    
    # Get all wishlist items with product data
    enhanced_wishlist = get_wishlist_items_with_products(session, query_params_dict)
    total_count = get_wishlist_count(session)
    
    # If no wishlist items found
    if not enhanced_wishlist:
        return api_response(200, "No wishlist items found", [], 0)
    
    return api_response(200, "All wishlists retrieved successfully", enhanced_wishlist, total_count)


# ✅ CHECK IF PRODUCT IS IN WISHLIST
@router.get("/check/{product_id}")
def check_in_wishlist(
    product_id: int,
    session: GetSession,
    user:requireSignin,
    variation_option_id: Optional[int] = None,
):
    # First, check if product exists
    product = session.get(Product, product_id)
    if not product:
        return api_response(404, "Product not found")

    query = select(Wishlist).where(
        Wishlist.user_id == user.get("id"),
        Wishlist.product_id == product_id
    )
    
    if variation_option_id is not None:
        query = query.where(Wishlist.variation_option_id == variation_option_id)
    else:
        query = query.where(Wishlist.variation_option_id.is_(None))

    wishlist_item = session.exec(query).first()
    
    if wishlist_item:
        # Enhance with product data for the response
        enhanced_item = WishlistReadWithProduct(
            id=wishlist_item.id,
            user_id=wishlist_item.user_id,
            product_id=wishlist_item.product_id,
            variation_option_id=wishlist_item.variation_option_id,
            created_at=wishlist_item.created_at,
            product=ProductReadForWishlist(
                id=product.id,
                name=product.name,
                price=product.price,
                sale_price=product.sale_price,
                image=product.image,
                in_stock=product.in_stock,
                slug=product.slug
            )
        )
        
        return api_response(200, "Product is in wishlist", {
            "in_wishlist": True,
            "wishlist_item": enhanced_item
        })
    else:
        return api_response(200, "Product is not in wishlist", {
            "in_wishlist": False,
            "product": ProductReadForWishlist(
                id=product.id,
                name=product.name,
                price=product.price,
                sale_price=product.sale_price,
                image=product.image,
                in_stock=product.in_stock,
                slug=product.slug
            )
        })


# ✅ GET WISHLIST BY USER ID (Admin or same user)
@router.get("/user/{user_id}")
def get_wishlist_by_user(
    user_id: int,
    query_params: ListQueryParams,
    session: GetSession,
    user:requireSignin
):
    # Allow users to view their own wishlist or admin to view any
    if user_id != user.id and not user.has_permission("wishlist:view_all"):
        return api_response(403, "Not authorized to view this user's wishlist")

    query_params_dict = vars(query_params)
    
    # Get wishlist items with product data for specific user
    enhanced_wishlist = get_wishlist_items_with_products(session, query_params_dict, user_id)
    total_count = get_wishlist_count(session, user_id)
    
    # If no wishlist items found
    if not enhanced_wishlist:
        return api_response(200, "No items in user's wishlist", [], 0)
    
    return api_response(200, "Wishlist retrieved successfully", enhanced_wishlist, total_count)