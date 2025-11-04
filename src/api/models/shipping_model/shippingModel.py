from typing import TYPE_CHECKING,Optional, Literal,List
from datetime import datetime
from sqlalchemy import Column, Enum
from pydantic import field_validator
from sqlmodel import SQLModel, Field,Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel
from enum import Enum as PyEnum

if TYPE_CHECKING:
    from src.api.models import (
        Order
    )

class ShippingType(PyEnum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    FREE_SHIPPING = "free_shipping"


class Shipping(TimeStampedModel, table=True):
    __tablename__: Literal["shipping_classes"] = "shipping_classes"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191, nullable=False)
    slug: str = Field(max_length=191, index=True, unique=True)
    amount: float = Field(nullable=False)
    is_global: bool = Field(default=True)   # <-- changed from str to bool
    is_active: bool = Field(default=True)
    language: str = Field(default="en", max_length=191)
    type: Optional[ShippingType] = ShippingType.FIXED

    # 🔴 NEW: Relationship with orders
    orders: List["Order"] = Relationship(back_populates="shipping")

class ShippingCreate(SQLModel):
    name: str
    amount: float
    type: Optional[ShippingType] = ShippingType.FIXED
    is_global: bool = True
    is_active: bool = True

class Config:
        use_enum_values = True   # <-- ensures enum gets dumped as "fixed"


class ShippingRead(TimeStampReadModel):
    id:int
    name: str
    amount: float
    type: ShippingType
    is_global: bool
    is_active: bool 

class Config:
        use_enum_values = True

class ShippingActivate(SQLModel):
    is_active: bool

class GlobalActivate(SQLModel):
    is_global: bool

class ShippingUpdate(SQLModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[ShippingType] = None
    is_active: Optional[bool] = None
    is_global: Optional[bool] = None
