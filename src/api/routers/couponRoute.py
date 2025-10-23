# src/api/routes/coupon.py
from fastapi import APIRouter
from sqlalchemy import select
from datetime import datetime
from sqlmodel import select
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)
from src.api.models.couponModel import Coupon, CouponCreate, CouponUpdate, CouponRead

router = APIRouter(prefix="/coupon", tags=["Coupon"])


# ✅ CREATE
@router.post("/create")
def create_coupon(
    request: CouponCreate,
    session: GetSession,
    user=requirePermission("system:*"),
):
    print("📦 Incoming coupon:", request.model_dump())

    coupon = Coupon(**request.model_dump())
    session.add(coupon)
    session.commit()
    session.refresh(coupon)

    return api_response(200, "Coupon created successfully", CouponRead.model_validate(coupon))


# ✅ UPDATE
@router.put("/update/{id}")
def update_coupon(
    id: int,
    request: CouponUpdate,
    session: GetSession,
    user=requirePermission("system:*"),
):
    coupon = session.get(Coupon, id)
    raiseExceptions((coupon, 404, "Coupon not found"))

    updated = updateOp(coupon, request, session)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Coupon updated successfully", CouponRead.model_validate(updated))


# ✅ READ BY ID
@router.get("/read/{id}")
def read_coupon_by_id(id: int, session: GetSession):
    coupon = session.get(Coupon, id)
    raiseExceptions((coupon, 404, "Coupon not found"))

    return api_response(200, "Coupon found", CouponRead.model_validate(coupon))


# ✅ READ BY Code (Redeem)
@router.get("/redeem/{code}")
def redeem_coupon(code: str, session: GetSession):
    """
    Validate and redeem a coupon by its code
    """
    # Query by code field instead of primary key id
    statement = select(Coupon).where(Coupon.code == code)
    coupon = session.exec(statement).first()
    
    # Check if coupon exists - MUST be checked first
    if not coupon:
        return api_response(404, "Coupon not found")
    
    current_time = datetime.utcnow()
    
    # Check if coupon is currently active
    if coupon.active_from > current_time:
        return api_response(400, "Coupon is not active yet", {
            "active_from": coupon.active_from.isoformat(),
            "current_time": current_time.isoformat()
        })
    
    if coupon.expire_at < current_time:
        return api_response(400, "Coupon has expired", {
            "expire_at": coupon.expire_at.isoformat(),
            "current_time": current_time.isoformat()
        })
    
    # If we reach here, coupon is valid
    return api_response(200, "Coupon found and is valid", CouponRead.model_validate(coupon))


# ✅ DELETE
@router.delete("/delete/{id}")
def delete_coupon(
    id: int,
    session: GetSession,
    user=requirePermission("system:*"),
):
    coupon = session.get(Coupon, id)
    raiseExceptions((coupon, 404, "Coupon not found"))

    session.delete(coupon)
    session.commit()
    return api_response(200, f"Coupon {coupon.code} deleted successfully")


# ✅ LIST (supports search + pagination)
@router.get("/list", response_model=list[CouponRead])
def list_coupons(query_params: ListQueryParams, user=requireSignin):
    query_params = vars(query_params)
    searchFields = ["code", "description", "language"]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Coupon,
        Schema=CouponRead,
    )