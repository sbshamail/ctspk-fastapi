# src/api/models/categoryModel.py
from typing import List, Optional
import datetime
from sqlmodel import Relationship, SQLModel, Field

from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel


class Category(TimeStampedModel, table=True):
    __tablename__ = "categories"

    # id: Optional[int] = Field(default=None, primary_key=True)
    # name: str = Field(max_length=191)
    # slug: str = Field(max_length=191)
    # language: str = Field(default="en", max_length=191)
    # icon: Optional[str] = None
    # image: Optional[dict] = None
    # details: Optional[str] = None
    # parent: Optional[int] = Field(default=None, foreign_key="categories.id")
    # type_id: int = Field(foreign_key="types.id")
    # admin_commission_rate: Optional[float] = None
    # is_active: bool = Field(default=True)
    # created_at: Optional[datetime.datetime] = None
    # updated_at: Optional[datetime.datetime] = None
    # deleted_at: Optional[datetime.datetime] = None

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, unique=True, max_length=100)
    description: Optional[str] = None

    parent_id: Optional[int] = Field(default=None, foreign_key="categories.id")
    parent: Optional["Category"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "categories.id"},
    )
    children: List["Category"] = Relationship(back_populates="parent")
    # products: List["Product"] = Relationship(back_populates="categories")


class CategoryCreate(SQLModel):
    title: str
    description: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryRead(TimeStampReadModel):
    id: int
    title: str
    description: Optional[str] = None
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True  # enable ORM mode / attribute mapping


class CategoryReadNested(TimeStampReadModel):
    id: int
    title: str
    description: str | None = None
    parent_id: int | None = None
    children: list["CategoryReadNested"] = Field(default_factory=list)

    class Config:
        from_attributes = True
