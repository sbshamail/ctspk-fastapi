# src/api/models/shopModel.py
from typing import Optional, List
import datetime
from sqlalchemy import Column
from sqlmodel import Field, Relationship
from sqlalchemy.dialects.postgresql import JSONB
from src.api.models.baseModel import TimeStampedModel


class Shop(TimeStampedModel, table=True):
    __tablename__ = "shops"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id")
    name: Optional[str] = Field(default=None, max_length=191)
    slug: Optional[str] = Field(default=None, max_length=191)
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
    products: List["Product"] = Relationship(back_populates="shop")
    balances: List["Balance"] = Relationship(back_populates="shop")

class ShopCreate(SQLModel):
    owner_id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool = False

class ShopRead(TimeStampReadModel):
    id: int
    owner_id: int
    name: str
    slug: str
    is_active: bool

class ShopUpdate(SQLModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None