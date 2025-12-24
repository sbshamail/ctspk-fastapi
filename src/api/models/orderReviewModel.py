# src/api/models/orderReviewModel.py
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_validator
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import User, Order


# --------------------------------------------------------------------
# MAIN MODEL
# --------------------------------------------------------------------
class OrderReview(TimeStampedModel, table=True):
    __tablename__ = "order_reviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True, unique=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    comment: Optional[str] = Field(default=None)
    rating: int = Field(ge=1, le=5)  # Rating between 1-5
    photos: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    deleted_at: Optional[datetime] = None

    # Relationships
    order: Optional["Order"] = Relationship(
        back_populates="order_review",
        sa_relationship_kwargs={"foreign_keys": "[OrderReview.order_id]"}
    )
    user: Optional["User"] = Relationship(back_populates="order_reviews")


# --------------------------------------------------------------------
# CRUD SCHEMAS
# --------------------------------------------------------------------
class OrderReviewCreate(SQLModel):
    order_id: int
    comment: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    photos: Optional[List[Dict[str, Any]]] = None

    @field_validator('photos', mode='before')
    @classmethod
    def empty_photos_to_none(cls, v):
        """Treat empty array or empty dict as None"""
        if v is None:
            return None
        if isinstance(v, list) and len(v) == 0:
            return None
        return v


class UserReadForOrderReview(SQLModel):
    id: int
    name: str
    avatar: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class OrderReviewRead(TimeStampReadModel):
    id: int
    order_id: int
    user_id: int
    comment: Optional[str] = None
    rating: int
    photos: Optional[List[Dict[str, Any]]] = None
    user: Optional[UserReadForOrderReview] = None


class OrderReviewUpdate(SQLModel):
    comment: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    photos: Optional[List[Dict[str, Any]]] = None

    @field_validator('photos', mode='before')
    @classmethod
    def empty_photos_to_none(cls, v):
        """Treat empty array or empty dict as None"""
        if v is None:
            return None
        if isinstance(v, list) and len(v) == 0:
            return None
        return v
