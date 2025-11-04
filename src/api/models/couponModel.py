# src/api/models/couponModel.py
from typing import Optional, Dict, Any,TYPE_CHECKING
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import (
        Order
    )

# --------------------------------------------------------------------
# ENUM: Coupon Types
# --------------------------------------------------------------------
class CouponType(str, Enum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    FREE_SHIPPING = "free_shipping"


# --------------------------------------------------------------------
# MAIN MODEL
# --------------------------------------------------------------------
class Coupon(TimeStampedModel, table=True):
    __tablename__ = "coupons"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=191)
    language: str = Field(default="en", max_length=10)
    description: Optional[str] = None
    image: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    type: CouponType = Field(default=CouponType.FIXED)
    amount: float = Field(default=0.0)
    minimum_cart_amount: float = Field(default=0.0)
    active_from: datetime = Field(default_factory=datetime.utcnow)
    expire_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    #orders: Optional["Order"] = Relationship(back_populates="coupon")

# --------------------------------------------------------------------
# CRUD SCHEMAS
# --------------------------------------------------------------------
class CouponCreate(SQLModel):
    code: str
    language: str = "en"
    type: CouponType = CouponType.FIXED
    amount: float
    minimum_cart_amount: float = 0.0
    active_from: datetime
    expire_at: datetime
    description: Optional[str] = None
    image: Optional[Dict[str, Any]] = None


class CouponRead(TimeStampReadModel):
    id: int
    code: str
    language: str
    type: CouponType
    amount: float
    minimum_cart_amount: float
    active_from: datetime
    expire_at: datetime
    description: Optional[str] = None
    image: Optional[Dict[str, Any]] = None


class CouponUpdate(SQLModel):
    language: Optional[str] = None
    description: Optional[str] = None
    type: Optional[CouponType] = None
    amount: Optional[float] = None
    minimum_cart_amount: Optional[float] = None
    active_from: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    image: Optional[Dict[str, Any]] = None
