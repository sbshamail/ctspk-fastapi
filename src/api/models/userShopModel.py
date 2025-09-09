# src/api/models/userShopModel.py
from typing import Optional
from sqlmodel import SQLModel, Field

from src.api.models.baseModel import TimeStampedModel


class UserShop(TimeStampedModel, table=True):
    __tablename__ = "user_shop"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    shop_id: int = Field(foreign_key="shops.id")
