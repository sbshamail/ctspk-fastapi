# tax_model.py
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

class Tax(TimeStampedModel, table=True):
    __tablename__: Literal["tax_classes"] = "tax_classes"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191, nullable=False)
    country: Optional[str] = Field(default=None, max_length=191)
    state: Optional[str] = Field(default=None, max_length=191)
    zip: Optional[str] = Field(default=None, max_length=191)
    city: Optional[str] = Field(default=None, max_length=191)
    rate: float = Field(nullable=False)
    is_global: bool = Field(default=True)
    priority: int = Field(default=1)
    on_shipping: bool = Field(default=False)

    orders: List["Order"] = Relationship(back_populates="tax")

class TaxCreate(SQLModel):
    name: str
    country: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    city: Optional[str] = None
    rate: float
    is_global: bool = True
    priority: int = 1
    on_shipping: bool = False

    class Config:
        use_enum_values = True


class TaxRead(TimeStampReadModel):
    id: int
    name: str
    country: Optional[str]
    state: Optional[str]
    zip: Optional[str]
    city: Optional[str]
    rate: float
    is_global: bool
    priority: int
    on_shipping: bool

    class Config:
        use_enum_values = True


class TaxActivate(SQLModel):
    is_global: bool


class TaxShippingToggle(SQLModel):
    on_shipping: bool


class TaxUpdate(SQLModel):
    name: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    city: Optional[str] = None
    rate: Optional[float] = None
    is_global: Optional[bool] = None
    priority: Optional[int] = None
    on_shipping: Optional[bool] = None