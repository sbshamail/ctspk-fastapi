# src/api/models/couponModel.py
from typing import Literal, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


class CouponType(str, Enum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    FREE_SHIPPING = "free_shipping"


class Coupon(TimeStampedModel, table=True):
    __tablename__: Literal["coupons"] = "coupons"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=191)
    language: str = Field(default="en", max_length=191)
    description: Optional[str] = None
    image: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    type: CouponType = Field(default=CouponType.FIXED)
    amount: float = Field(default=0.00)
    minimum_cart_amount: float = Field(default=0.00)
    active_from: str = Field(max_length=191)
    expire_at: str = Field(max_length=191)
    deleted_at: Optional[datetime] = None


class CouponCreate(SQLModel):
    code: str
    type: CouponType = CouponType.FIXED
    amount: float
    active_from: str
    expire_at: str
    minimum_cart_amount: float = 0.00


class CouponRead(TimeStampReadModel):
    id: int
    code: str
    type: CouponType
    amount: float


class CouponUpdate(SQLModel):
    amount: Optional[float] = None
    minimum_cart_amount: Optional[float] = None
    expire_at: Optional[str] = None
