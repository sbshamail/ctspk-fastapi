# src/api/routes/review.py
from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import select, func
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)
from src.api.models.reviewModel import Review, ReviewCreate, ReviewUpdate, ReviewRead, UserReadForReview

router = APIRouter(prefix="/review", tags=["Review"])


def build_review_response(review: Review) -> dict:
    """Build review response with user info (avatar from image)"""
    review_data = {
        "id": review.id,
        "order_id": review.order_id,
        "user_id": review.user_id,
        "shop_id": review.shop_id,
        "product_id": review.product_id,
        "variation_option_id": review.variation_option_id,
        "comment": review.comment,
        "rating": review.rating,
        "photos": review.photos,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "user": None
    }

    if review.user:
        review_data["user"] = {
            "id": review.user.id,
            "name": review.user.name,
            "avatar": review.user.image  # Use image as avatar
        }

    return review_data


# ✅ CREATE REVIEW
@router.post("/create")
def create_review(
    request: ReviewCreate,
    session: GetSession,
    user:requireSignin
):
    print("📝 Incoming review:", request.model_dump())

    # Check if review already exists for this order and product
    existing_review = session.exec(
        select(Review).where(
            Review.order_id == request.order_id,
            Review.product_id == request.product_id,
            Review.user_id == user.get("id"),
            Review.deleted_at.is_(None)
        )
    ).first()
    
    if existing_review:
        return api_response(400, "Review already exists for this order and product")
    
    from src.api.models.order_model.orderModel import Order, OrderProduct
    order = session.get(Order, request.order_id)
    
    if order.customer_id != user.get("id"):
        return api_response(403, "You are not authorized to review this order")
    
    # Check if product exists in this order
    order_item_stmt = select(OrderProduct).where(
        OrderProduct.order_id == request.order_id,
        OrderProduct.product_id == request.product_id
    )
    order_item = session.execute(order_item_stmt).scalars().first()

    if not order_item:
        return api_response(400, f"Product {request.product_id} not found in order {request.order_id}")

    # Create review with user_id from token
    review_data = request.model_dump()
    review_data["user_id"] = user.get("id")
    review = Review(**review_data)
    session.add(review)
    session.flush()  # Get the review ID without committing

    # Save review_id in OrderProduct (re-fetch to ensure fresh object)
    order_item_update = session.execute(
        select(OrderProduct).where(
            OrderProduct.order_id == request.order_id,
            OrderProduct.product_id == request.product_id
        )
    ).scalars().first()

    if order_item_update:
        order_item_update.review_id = review.id
        session.add(order_item_update)

    session.commit()
    session.refresh(review)

    print(f"✅ Review #{review.id} created, order_item.review_id updated to {review.id}")

    # Update product rating and review count
    from src.api.models.product_model.productsModel import Product

    # Calculate average rating and review count for this product
    result = session.exec(
        select(
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count")
        ).where(
            Review.product_id == request.product_id,
            Review.deleted_at.is_(None)
        )
    ).first()

    avg_rating = float(result.avg_rating) if result.avg_rating else 0.0
    review_count = result.review_count or 0

    # Update the product
    product = session.get(Product, request.product_id)
    if product:
        product.rating = round(avg_rating, 2)
        product.review_count = review_count
        session.add(product)
        session.commit()

    # Load user relationship for response
    from src.api.models.usersModel import User
    review_user = session.get(User, review.user_id)
    review.user = review_user

    return api_response(201, "Review created successfully", build_review_response(review))


# ✅ UPDATE REVIEW
@router.put("/update/{id}")
def update_review(
    id: int,
    request: ReviewUpdate,
    session: GetSession,
    user:requireSignin
):
    review = session.get(Review, id)
    raiseExceptions((review, 404, "Review not found"))
    
    # Check if review is deleted
    if review.deleted_at is not None:
        return api_response(404, "Review has been deleted")

    if review.user_id != user.get("id"):
        return api_response(403, "You are not authorized to update this review")
    updated = updateOp(review, request, session)
    session.commit()
    session.refresh(updated)

    # Update product rating and review count if rating was changed
    if request.rating is not None:
        from src.api.models.product_model.productsModel import Product

        result = session.exec(
            select(
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("review_count")
            ).where(
                Review.product_id == review.product_id,
                Review.deleted_at.is_(None)
            )
        ).first()

        avg_rating = float(result.avg_rating) if result.avg_rating else 0.0
        review_count = result.review_count or 0

        product = session.get(Product, review.product_id)
        if product:
            product.rating = round(avg_rating, 2)
            product.review_count = review_count
            session.add(product)
            session.commit()

    # Load user relationship for response
    from src.api.models.usersModel import User
    review_user = session.get(User, updated.user_id)
    updated.user = review_user

    return api_response(200, "Review updated successfully", build_review_response(updated))


# ✅ READ REVIEW BY ID
@router.get("/read/{id}")
def read_review(id: int, session: GetSession):
    review = session.get(Review, id)
    raiseExceptions((review, 404, "Review not found"))

    # Check if review is deleted
    if review.deleted_at is not None:
        return api_response(404, "Review has been deleted")

    # Load user relationship for response
    from src.api.models.usersModel import User
    review_user = session.get(User, review.user_id)
    review.user = review_user

    return api_response(200, "Review found", build_review_response(review))


# ✅ SOFT DELETE REVIEW
@router.delete("/delete/{id}")
def delete_review(
    id: int,
    session: GetSession,
    user:requireSignin
):
    review = session.get(Review, id)
    raiseExceptions((review, 404, "Review not found"))
    
    if review.user_id != user.get("id"):
        return api_response(403, "You are not authorized to delete this review")

    product_id = review.product_id
    order_id = review.order_id

    # Soft delete by setting deleted_at timestamp
    review.deleted_at = datetime.utcnow()
    session.commit()

    # Remove review_id from OrderProduct
    from src.api.models.order_model.orderModel import OrderProduct
    order_item_stmt = select(OrderProduct).where(
        OrderProduct.order_id == order_id,
        OrderProduct.product_id == product_id
    )
    order_item = session.execute(order_item_stmt).scalars().first()
    if order_item:
        print(f"🗑️ Removing review_id {order_item.review_id} from order_item for order {order_id}, product {product_id}")
        order_item.review_id = None
        session.add(order_item)
        session.commit()
        print(f"✅ order_item.review_id set to None")

    # Update product rating and review count after deletion
    from src.api.models.product_model.productsModel import Product

    result = session.exec(
        select(
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count")
        ).where(
            Review.product_id == product_id,
            Review.deleted_at.is_(None)
        )
    ).first()

    avg_rating = float(result.avg_rating) if result.avg_rating else 0.0
    review_count = result.review_count or 0

    product = session.get(Product, product_id)
    if product:
        product.rating = round(avg_rating, 2)
        product.review_count = review_count
        session.add(product)
        session.commit()

    return api_response(200, f"Review #{review.id} deleted successfully")


# ✅ LIST REVIEWS (supports search + pagination)
@router.get("/list", response_model=list[ReviewRead])
def list_reviews(query_params: ListQueryParams, user=requireSignin):
    query_params = vars(query_params)
    searchFields = ["comment"]
    
    # Only show non-deleted reviews by default
    if "filters" not in query_params:
        query_params["filters"] = {}
    query_params["filters"]["deleted_at"] = None
    
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Review,
        Schema=ReviewRead,
    )


# ✅ GET REVIEWS BY PRODUCT
@router.get("/product/{product_id}")
def get_reviews_by_product(
    product_id: int,
    session: GetSession,
):
    from src.api.models.usersModel import User
    from sqlmodel import Session

    # Query reviews for this product
    statement = select(Review).where(
        Review.product_id == product_id,
        Review.deleted_at.is_(None)
    ).order_by(Review.created_at.desc())

    reviews = session.execute(statement).scalars().all()

    # Build response with user info
    reviews_data = []
    for review in reviews:
        user = session.get(User, review.user_id)
        review.user = user
        reviews_data.append(build_review_response(review))

    return api_response(200, "Reviews found", reviews_data)


# ✅ GET REVIEWS BY USER
@router.get("/user/{user_id}")
def get_reviews_by_user(
    user_id: int,
    session: GetSession,
    user: requireSignin
):
    from src.api.models.usersModel import User

    # Query reviews for this user
    statement = select(Review).where(
        Review.user_id == user_id,
        Review.deleted_at.is_(None)
    ).order_by(Review.created_at.desc())

    reviews = session.execute(statement).scalars().all()

    # Build response with user info
    reviews_data = []
    for review in reviews:
        review_user = session.get(User, review.user_id)
        review.user = review_user
        reviews_data.append(build_review_response(review))

    return api_response(200, "Reviews found", reviews_data)


# ✅ GET REVIEWS BY SHOP
@router.get("/shop/{shop_id}")
def get_reviews_by_shop(
    shop_id: int,
    session: GetSession,
    user=requireSignin
):
    from src.api.models.usersModel import User

    # Query reviews for this shop
    statement = select(Review).where(
        Review.shop_id == shop_id,
        Review.deleted_at.is_(None)
    ).order_by(Review.created_at.desc())

    reviews = session.execute(statement).scalars().all()

    # Build response with user info
    reviews_data = []
    for review in reviews:
        review_user = session.get(User, review.user_id)
        review.user = review_user
        reviews_data.append(build_review_response(review))

    return api_response(200, "Reviews found", reviews_data)