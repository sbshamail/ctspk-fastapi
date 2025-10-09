# src/api/models/reviewModel.py
from typing import Optional, Dict, Any,TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Column, JSON, ForeignKey
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import User, Product,VariationOption,Shop,Order
# --------------------------------------------------------------------
# MAIN MODEL
# --------------------------------------------------------------------
class Review(TimeStampedModel, table=True):
    __tablename__ = "reviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    shop_id: int = Field(foreign_key="shops.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    variation_option_id: Optional[int] = Field(
        default=None, 
        foreign_key="variation_options.id", 
        index=True
    )
    comment: Optional[str] = Field(default=None)
    rating: int = Field(ge=1, le=5)  # Rating between 1-5
    photos: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    deleted_at: Optional[datetime] = None

    # Relationships (optional - for eager loading if needed)
    order: Optional["Order"] = Relationship(back_populates="reviews")
    user: Optional["User"] = Relationship(back_populates="reviews")
    shop: Optional["Shop"] = Relationship(back_populates="reviews")
    product: Optional["Product"] = Relationship(back_populates="reviews")
    variation_option: Optional["VariationOption"] = Relationship(back_populates="reviews")


# --------------------------------------------------------------------
# CRUD SCHEMAS
# --------------------------------------------------------------------
class ReviewCreate(SQLModel):
    order_id: int
    user_id: int
    shop_id: int
    product_id: int
    variation_option_id: Optional[int] = None
    comment: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    photos: Optional[Dict[str, Any]] = None


class ReviewRead(TimeStampReadModel):
    id: int
    order_id: int
    user_id: int
    shop_id: int
    product_id: int
    variation_option_id: Optional[int] = None
    comment: Optional[str] = None
    rating: int
    photos: Optional[Dict[str, Any]] = None


class ReviewUpdate(SQLModel):
    variation_option_id: Optional[int] = None
    comment: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    photos: Optional[Dict[str, Any]] = None