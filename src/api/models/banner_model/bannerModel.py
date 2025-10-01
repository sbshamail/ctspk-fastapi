from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, List
from sqlmodel import JSON, Column, SQLModel, Field, Relationship
from src.api.models.category_model.categoryModel import CategoryRead
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel


if TYPE_CHECKING:
    from src.api.models import Category


class Banner(TimeStampedModel, table=True):
    __tablename__: Literal["banners"] = "banners"

    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: Optional[int] = Field(foreign_key="categories.id")
    name: str = Field(max_length=191)
    slug: str = Field(max_length=191, index=True, unique=True)
    language: str = Field(default="en", max_length=191)
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    image: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
    )
    # Relationships
    category: Optional["Category"] = Relationship(back_populates="banners")


class BannerCreate(SQLModel):
    category_id: Optional[int] = None
    name: str
    description: str
    image: Optional[Dict[str, Any]] = None


class BannerUpdate(SQLModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[Dict[str, Any]] = None


class BannerRead(TimeStampReadModel):
    id: int
    name: str
    description: Optional[str] = None
    slug: str
    image: Optional[Dict[str, Any]] = None
    is_active: bool
    category: Optional[CategoryRead] = None

    class Config:
        from_attributes = True
