# src/api/models/shopModel.py
from typing import Literal, Optional, List, TYPE_CHECKING
from sqlalchemy import Column
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.dialects.postgresql import JSONB
from src.api.models.usersModel import UserReadBase
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import User, UserShop, Product,Order,Review,ShopWithdrawRequest,ShopEarning



class Shop(TimeStampedModel, table=True):
    __tablename__: Literal["shops"] = "shops"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id")
    name: Optional[str] = Field(default=None, max_length=191, unique=True)
    slug: Optional[str] = Field(default=None, max_length=191, index=True, unique=True)
    description: Optional[str] = None
    cover_image: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    logo: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    is_active: bool = Field(default=False)
    address: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    settings: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    notifications: Optional[dict] = Field(default=None, sa_column=Column(JSONB))

    owner: "User" = Relationship(
        back_populates="shops",
        sa_relationship_kwargs={"foreign_keys": "[Shop.owner_id]"},
    )
    user_shops: list["UserShop"] = Relationship(back_populates="shop")

    products: List["Product"] = Relationship(back_populates="shop")
    withdraw_requests: Optional["ShopWithdrawRequest"] = Relationship(back_populates="shop")
    earnings: Optional["ShopEarning"] = Relationship(back_populates="shop")
    # balances: List["Balance"] = Relationship(back_populates="shop")
   # orders: List["Order"] = Relationship(back_populates="shop")
    # orders: List["Order"] = Relationship(
    #     back_populates="shop",
    #     sa_relationship_kwargs={
    #         "foreign_keys": "[Order.shop_id]"
    #     }
    # )
    reviews: Optional["Review"] = Relationship(back_populates="shop")

class ShopCreate(SQLModel):
    name: str
    description: Optional[str] = None
    cover_image: Optional[dict] = None
    logo: Optional[dict] = None
    address: Optional[dict] = None
    settings: Optional[dict] = None
    notifications: Optional[dict] = None


class ShopVerifyByAdmin(SQLModel):
    is_active: bool


# ---------- UPDATE ----------
class ShopUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[dict] = None
    logo: Optional[dict] = None
    address: Optional[dict] = None
    settings: Optional[dict] = None
    notifications: Optional[dict] = None
    is_active: Optional[bool] = None


# ---------- READ ----------
class ShopRead(TimeStampReadModel):
    id: int
    owner_id: int
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[dict] = None
    logo: Optional[dict] = None
    is_active: bool
    address: Optional[dict] = None
    settings: Optional[dict] = None
    notifications: Optional[dict] = None

    # include nested owner
    owner: Optional[UserReadBase] = None

    model_config = {"from_attributes": True}
