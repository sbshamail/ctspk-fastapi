# src/api/models/walletModel.py
from typing import TYPE_CHECKING, Literal, Optional
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import User


class Wallet(TimeStampedModel, table=True):
    __tablename__: Literal["wallets"] = "wallets"

    id: Optional[int] = Field(default=None, primary_key=True)
    total_points: float = Field(default=0)
    points_used: float = Field(default=0)
    available_points: float = Field(default=0)
    customer_id: Optional[int] = Field(foreign_key="users.id")

    # relationships
    customer: "User" = Relationship()


class WalletCreate(SQLModel):
    customer_id: int
    total_points: float = 0


class WalletRead(TimeStampReadModel):
    id: int
    customer_id: int
    total_points: float
    available_points: float


class WalletUpdate(SQLModel):
    total_points: Optional[float] = None
    points_used: Optional[float] = None
