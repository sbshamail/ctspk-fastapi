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
    name: str = Field(max_length=191)
    is_approved: bool = Field(default=False)
    image: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    cover_image: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    slug: str = Field(max_length=191)
    language: str = Field(default="en", max_length=191)
    type_id: int = Field(foreign_key="types.id")
    description: Optional[str] = None
    website: Optional[str] = Field(max_length=191)
    socials: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    is_active: bool = Field(default=True)

    # relationships
    type: "Type" = Relationship()
    products: List["Product"] = Relationship(back_populates="manufacturer")


class ManufacturerCreate(SQLModel):
    name: str
    slug: str
    type_id: int
    is_approved: bool = False
    is_active: bool = True


class ManufacturerRead(TimeStampReadModel):
    id: int
    name: str
    slug: str
    is_approved: bool
    is_active: bool


class ManufacturerUpdate(SQLModel):
    name: Optional[str] = None
    is_approved: Optional[bool] = None
    is_active: Optional[bool] = None
