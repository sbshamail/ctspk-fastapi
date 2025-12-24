# src/api/routes/orderReview.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)
from src.api.models.orderReviewModel import (
    OrderReview,
    OrderReviewCreate,
    OrderReviewUpdate,
    OrderReviewRead,
    UserReadForOrderReview,
)

router = APIRouter(prefix="/order-review", tags=["Order Review"])


def build_order_review_response(review: OrderReview) -> dict:
    """Build order review response with user info"""
    review_data = {
        "id": review.id,
        "order_id": review.order_id,
        "user_id": review.user_id,
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


# CREATE ORDER REVIEW
@router.post("/create")
def create_order_review(
    request: OrderReviewCreate,
    session: GetSession,
    user: requireSignin
):
    # Check if review already exists for this order
    existing_review = session.exec(
        select(OrderReview).where(
            OrderReview.order_id == request.order_id,
            OrderReview.deleted_at.is_(None)
        )
    ).first()

    if existing_review:
        return api_response(400, "Review already exists for this order")

    # Validate order exists and belongs to user
    from src.api.models.order_model.orderModel import Order
    order = session.get(Order, request.order_id)

    if not order:
        return api_response(404, "Order not found")

    if order.customer_id != user.get("id"):
        return api_response(403, "You are not authorized to review this order")

    # Create review with user_id from token
    review_data = request.model_dump()
    review_data["user_id"] = user.get("id")
    review = OrderReview(**review_data)
    session.add(review)
    session.flush()

    # Update order with order_review_id
    order.order_review_id = review.id
    session.add(order)

    session.commit()
    session.refresh(review)

    # Load user relationship for response
    from src.api.models.usersModel import User
    review_user = session.get(User, review.user_id)
    review.user = review_user

    return api_response(201, "Order review created successfully", build_order_review_response(review))


# UPDATE ORDER REVIEW
@router.put("/update/{id}")
def update_order_review(
    id: int,
    request: OrderReviewUpdate,
    session: GetSession,
    user: requireSignin
):
    review = session.get(OrderReview, id)
    raiseExceptions((review, 404, "Order review not found"))

    # Check if review is deleted
    if review.deleted_at is not None:
        return api_response(404, "Order review has been deleted")

    if review.user_id != user.get("id"):
        return api_response(403, "You are not authorized to update this review")

    updated = updateOp(review, request, session)
    session.commit()
    session.refresh(updated)

    # Load user relationship for response
    from src.api.models.usersModel import User
    review_user = session.get(User, updated.user_id)
    updated.user = review_user

    return api_response(200, "Order review updated successfully", build_order_review_response(updated))


# READ ORDER REVIEW BY ID
@router.get("/read/{id}")
def read_order_review(id: int, session: GetSession):
    review = session.get(OrderReview, id)
    raiseExceptions((review, 404, "Order review not found"))

    # Check if review is deleted
    if review.deleted_at is not None:
        return api_response(404, "Order review has been deleted")

    # Load user relationship for response
    from src.api.models.usersModel import User
    review_user = session.get(User, review.user_id)
    review.user = review_user

    return api_response(200, "Order review found", build_order_review_response(review))


# READ ORDER REVIEW BY ORDER ID
@router.get("/order/{order_id}")
def read_order_review_by_order(order_id: int, session: GetSession):
    review = session.exec(
        select(OrderReview).where(
            OrderReview.order_id == order_id,
            OrderReview.deleted_at.is_(None)
        )
    ).first()

    if not review:
        return api_response(404, "Order review not found for this order")

    # Load user relationship for response
    from src.api.models.usersModel import User
    review_user = session.get(User, review.user_id)
    review.user = review_user

    return api_response(200, "Order review found", build_order_review_response(review))


# SOFT DELETE ORDER REVIEW
@router.delete("/delete/{id}")
def delete_order_review(
    id: int,
    session: GetSession,
    user: requireSignin
):
    review = session.get(OrderReview, id)
    raiseExceptions((review, 404, "Order review not found"))

    if review.user_id != user.get("id"):
        return api_response(403, "You are not authorized to delete this review")

    order_id = review.order_id

    # Soft delete by setting deleted_at timestamp
    review.deleted_at = datetime.utcnow()
    session.add(review)

    # Remove order_review_id from Order
    from src.api.models.order_model.orderModel import Order
    order = session.get(Order, order_id)
    if order:
        order.order_review_id = None
        session.add(order)

    session.commit()

    return api_response(200, f"Order review #{review.id} deleted successfully")


# LIST ORDER REVIEWS
@router.get("/list", response_model=list[OrderReviewRead])
def list_order_reviews(query_params: ListQueryParams, user=requireSignin):
    query_params = vars(query_params)
    searchFields = ["comment"]

    # Only show non-deleted reviews by default
    if "customFilters" not in query_params or query_params["customFilters"] is None:
        query_params["customFilters"] = []
    query_params["customFilters"].append(["deleted_at", None])

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=OrderReview,
        Schema=OrderReviewRead,
    )


# GET ORDER REVIEWS BY USER
@router.get("/user/{user_id}")
def get_order_reviews_by_user(
    user_id: int,
    session: GetSession,
    user: requireSignin
):
    from src.api.models.usersModel import User

    # Query reviews for this user
    statement = select(OrderReview).where(
        OrderReview.user_id == user_id,
        OrderReview.deleted_at.is_(None)
    ).order_by(OrderReview.created_at.desc())

    reviews = session.execute(statement).scalars().all()

    # Build response with user info
    reviews_data = []
    for review in reviews:
        review_user = session.get(User, review.user_id)
        review.user = review_user
        reviews_data.append(build_order_review_response(review))

    return api_response(200, "Order reviews found", reviews_data)


# GET MY ORDER REVIEWS (for authenticated user)
@router.get("/my-reviews")
def get_my_order_reviews(
    session: GetSession,
    user: requireSignin
):
    from src.api.models.usersModel import User

    user_id = user.get("id")

    # Query reviews for authenticated user
    statement = select(OrderReview).where(
        OrderReview.user_id == user_id,
        OrderReview.deleted_at.is_(None)
    ).order_by(OrderReview.created_at.desc())

    reviews = session.execute(statement).scalars().all()

    # Build response with user info
    reviews_data = []
    for review in reviews:
        review_user = session.get(User, review.user_id)
        review.user = review_user
        reviews_data.append(build_order_review_response(review))

    return api_response(200, "Order reviews found", reviews_data)
