# src/api/models/wishlistModel.py
from typing import Optional
import datetime
from sqlmodel import SQLModel, Field, Relationship

from src.api.models.baseModel import TimeStampedModel


class Wishlist(TimeStampedModel, table=True):
    __tablename__ = "wishlists"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    product_id: int = Field(foreign_key="products.id")
    variation_option_id: Optional[int] = Field(
        default=None, foreign_key="variation_options.id"
    )
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    user: Optional["User"] = Relationship(back_populates="wishlists")
    product: Optional["Product"] = Relationship(back_populates="wishlists")
