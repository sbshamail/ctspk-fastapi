# src/api/models/manufacturerModel.py
from typing import TYPE_CHECKING, Literal, Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import Product, Type


class Manufacturer(TimeStampedModel, table=True):
    __tablename__: Literal["manufacturers"] = "manufacturers"
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(max_length=191, index=True, unique=True)  # ✅ indexed + unique
    name: str = Field(max_length=191)
    is_approved: bool = Field(default=False)
    image: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    cover_image: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    language: str = Field(default="en", max_length=191)
    description: Optional[str] = None
    website: Optional[str] = Field(max_length=191)
    socials: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    is_active: bool = Field(default=True)

    # relationships
    products: List["Product"] = Relationship(back_populates="manufacturer")


class ManufacturerCreate(SQLModel):
    name: str
    is_approved: bool = False
    is_active: bool = True
    description: str
    image: Optional[Dict[str, Any]] = None
    cover_image: Optional[Dict[str, Any]] = None
    website: str


class ManufacturerRead(TimeStampReadModel):
    id: int
    slug: str
    name: str
    is_approved: bool
    is_active: bool
    description: Optional[str] = None
    image: Optional[Dict[str, Any]] = None
    cover_image: Optional[Dict[str, Any]] = None
    website: Optional[str] = None


class ManufacturerUpdate(SQLModel):
    name: Optional[str] = None
    # type_id: Optional[int] = None
    is_approved: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    image: Optional[Dict[str, Any]] = None
    cover_image: Optional[Dict[str, Any]] = None
    website: Optional[str] = None
