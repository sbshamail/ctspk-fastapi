from typing import Literal, Optional
from sqlalchemy import Column, Enum
from datetime import datetime
from sqlmodel import SQLModel, Field
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel
from enum import Enum as PyEnum


class ShippingType(PyEnum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    FREE_SHIPPING = "free_shipping"


class Shipping(TimeStampedModel, table=True):
    __tablename__: Literal["shipping_classes"] = "shipping_classes"

    # Use mapper arguments to handle the conflict
    __mapper_args__ = {"column_prefix": "_"}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191, nullable=False)
    slug: str = Field(max_length=191, index=True, unique=True)  # ✅ indexed + unique
    amount: float = Field(nullable=False)
    is_global: str = Field(default="1", max_length=191)
    is_active: bool = Field(default=True)
    language: str = Field(default="en", max_length=191)
    type: ShippingType = Field(
        sa_column=Column(Enum(ShippingType), default=ShippingType.FIXED)
    )


class ShippingCreate(SQLModel):
    name: str
    amount: float
    type: Optional[ShippingType] = None
    is_global: bool = True
    is_active: bool = True

class ShippingRead(TimeStampReadModel):
    name: str
    amount: float
    type: ShippingType
    is_global: bool
    is_active: bool 

class ShippingActivate(SQLModel):
    is_active: bool

class ShippingUpdate(SQLModel):
    name: str
    amount: float
    type: Optional[ShippingType] = None
    is_active: bool = True
    is_global: bool = True