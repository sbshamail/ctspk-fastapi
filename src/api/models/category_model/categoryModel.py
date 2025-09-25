# src/api/models/categoryModel.py
from typing import TYPE_CHECKING, Literal, Optional, List, Dict, Any
from sqlalchemy import Column, JSON
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import Product


class Category(TimeStampedModel, table=True):
    __tablename__ = "categories"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191)
    slug: str = Field(max_length=191)
    level: int = Field(default=1)  # 1, 2, or 3
    language: str = Field(default="en", max_length=191)
    icon: Optional[str] = Field(max_length=191)
    image: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    details: Optional[str] = None
    # own forien id
    parent_id: Optional[int] = Field(default=None, foreign_key="categories.id")

    admin_commission_rate: Optional[float] = None
    is_active: bool = Field(default=True)
    deleted_at: Optional[datetime] = None

    # relationships
    parent: Optional["Category"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Category.id"},
    )
    children: List["Category"] = Relationship(back_populates="parent")
    products: List["Product"] = Relationship(back_populates="category")


class CategoryCreate(SQLModel):
    name: str
    slug: str
    parent_id: Optional[int] = None
    details: Optional[str] = None
    image: Optional[Dict[str, Any]] = None
    is_active: bool = True
    icon: Optional[str] = None
    admin_commission_rate: Optional[float] = None


class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None
    parent_id: Optional[int] = None
    details: Optional[str] = None
    image: Optional[Dict[str, Any]] = None
    is_active: bool = True
    icon: Optional[str] = None
    admin_commission_rate: Optional[float] = None


class CategoryRead(TimeStampReadModel):
    id: int
    name: str
    slug: str
    image: Dict[str, Any] | None = None
    details: Optional[str] = None
    slug: Optional[str] = None
    is_active: bool
    parent_id: Optional[int] = None


class CategoryReadNested(TimeStampReadModel):
    id: int
    name: str
    details: Optional[str] = None
    image: Dict[str, Any] | None = None
    slug: Optional[str] = None
    parent_id: int | None = None
    is_active: bool
    children: list["CategoryReadNested"] = Field(default_factory=list)

    class Config:
        from_attributes = True
