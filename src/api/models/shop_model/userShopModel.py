# src/api/models/userShopModel.py
from typing import TYPE_CHECKING, Literal, Optional
from sqlmodel import Relationship, SQLModel, Field

from src.api.models.shop_model.shopsModel import ShopRead
from src.api.models.usersModel import UserReadBase
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel


if TYPE_CHECKING:
    from src.api.models import User, Shop


class UserShop(TimeStampedModel, table=True):
    __tablename__: Literal["user_shop"] = "user_shop"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    shop_id: int = Field(foreign_key="shops.id")
    # relationships
    user: "User" = Relationship(back_populates="user_shops")
    shop: "Shop" = Relationship(back_populates="user_shops")


class UserShopCreate(SQLModel):
    user_id: int
    shop_id: int


class UserShopRead(TimeStampReadModel):
    id: int
    user_id: int
    shop_id: int
    user: Optional[UserReadBase] = None
    shop: Optional[ShopRead] = None

    model_config = {"from_attributes": True}
