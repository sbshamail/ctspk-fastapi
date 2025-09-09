# src/api/models/walletModel.py
from typing import Optional
import datetime
from sqlmodel import SQLModel, Field, Relationship

from src.api.models.baseModel import TimeStampedModel


class Wallet(TimeStampedModel, table=True):
    __tablename__ = "wallets"

    id: Optional[int] = Field(default=None, primary_key=True)
    total_points: float = Field(default=0)
    points_used: float = Field(default=0)
    available_points: float = Field(default=0)
    customer_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    user: Optional["User"] = Relationship(back_populates="wallets")
