# src/api/routes/review.py
from fastapi import APIRouter
from sqlalchemy import select
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)
from src.api.models.reviewModel import Review, ReviewCreate, ReviewUpdate, ReviewRead

router = APIRouter(prefix="/review", tags=["Review"])


# ✅ CREATE REVIEW
@router.post("/create")
def create_review(
    request: ReviewCreate,
    session: GetSession,
    #user=requirePermission("review:create"),
):
    print("📝 Incoming review:", request.model_dump())

    # Check if review already exists for this order and product
    existing_review = session.exec(
        select(Review).where(
            Review.order_id == request.order_id,
            Review.product_id == request.product_id,
            Review.deleted_at.is_(None)
        )
    ).first()
    
    if existing_review:
        return api_response(400, "Review already exists for this order and product")

    review = Review(**request.model_dump())
    session.add(review)
    session.commit()
    session.refresh(review)

    return api_response(201, "Review created successfully", ReviewRead.model_validate(review))


# ✅ UPDATE REVIEW
@router.put("/update/{id}")
def update_review(
    id: int,
    request: ReviewUpdate,
    session: GetSession,
    user=requirePermission("review:update"),
):
    review = session.get(Review, id)
    raiseExceptions((review, 404, "Review not found"))
    
    # Check if review is deleted
    if review.deleted_at is not None:
        return api_response(404, "Review has been deleted")

    updated = updateOp(review, request, session)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Review updated successfully", ReviewRead.model_validate(updated))


# ✅ READ REVIEW BY ID
@router.get("/read/{id}")
def read_review(id: int, session: GetSession):
    review = session.get(Review, id)
    raiseExceptions((review, 404, "Review not found"))
    
    # Check if review is deleted
    if review.deleted_at is not None:
        return api_response(404, "Review has been deleted")

    return api_response(200, "Review found", ReviewRead.model_validate(review))


# ✅ SOFT DELETE REVIEW
@router.delete("/delete/{id}")
def delete_review(
    id: int,
    session: GetSession,
    user=requirePermission("review:delete"),
):
    review = session.get(Review, id)
    raiseExceptions((review, 404, "Review not found"))
    
    # Soft delete by setting deleted_at timestamp
    review.deleted_at = datetime.utcnow()
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
@router.get("/product/{product_id}", response_model=list[ReviewRead])
def get_reviews_by_product(
    product_id: int,
    query_params: ListQueryParams,
    session: GetSession,
    user=requireSignin
):
    query_params = vars(query_params)
    
    # Add product filter
    if "filters" not in query_params:
        query_params["filters"] = {}
    query_params["filters"]["product_id"] = product_id
    query_params["filters"]["deleted_at"] = None
    
    searchFields = ["comment"]
    
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Review,
        Schema=ReviewRead,
    )


# ✅ GET REVIEWS BY USER
@router.get("/user/{user_id}", response_model=list[ReviewRead])
def get_reviews_by_user(
    user_id: int,
    query_params: ListQueryParams,
    session: GetSession,
    user=requireSignin
):
    query_params = vars(query_params)
    
    # Add user filter
    if "filters" not in query_params:
        query_params["filters"] = {}
    query_params["filters"]["user_id"] = user_id
    query_params["filters"]["deleted_at"] = None
    
    searchFields = ["comment"]
    
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Review,
        Schema=ReviewRead,
    )


# ✅ GET REVIEWS BY SHOP
@router.get("/shop/{shop_id}", response_model=list[ReviewRead])
def get_reviews_by_shop(
    shop_id: int,
    query_params: ListQueryParams,
    session: GetSession,
    user=requireSignin
):
    query_params = vars(query_params)
    
    # Add shop filter
    if "filters" not in query_params:
        query_params["filters"] = {}
    query_params["filters"]["shop_id"] = shop_id
    query_params["filters"]["deleted_at"] = None
    
    searchFields = ["comment"]
    
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Review,
        Schema=ReviewRead,
    )