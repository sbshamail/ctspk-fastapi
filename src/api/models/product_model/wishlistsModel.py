# src/api/models/wishlistModel.py
from typing import TYPE_CHECKING, Literal, Optional
import datetime
from sqlmodel import SQLModel, Field, Relationship

from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import User, Product


class Wishlist(TimeStampedModel, table=True):
    __tablename__: Literal["wishlists"] = "wishlists"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    product_id: int = Field(foreign_key="products.id")
    variation_option_id: Optional[int] = Field(
        default=None, foreign_key="variation_options.id"
    )

    user: Optional["User"] = Relationship(back_populates="wishlists")
    product: Optional["Product"] = Relationship(back_populates="wishlists")


class WishlistCreate(SQLModel):
    user_id: int
    product_id: int
    variation_option_id: Optional[int] = None


class WishlistRead(TimeStampReadModel):
    id: int
    user_id: int
    product_id: int
    variation_option_id: Optional[int]
