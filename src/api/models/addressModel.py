##############DONE
# src/api/models/addressModel.py
from typing import TYPE_CHECKING, Literal, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import User


class Address(TimeStampedModel, table=True):
    __tablename__: Literal["address"] = "address"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=191)
    type: str = Field(max_length=191)
    default: bool = Field(default=False)
    address: Dict[str, Any] = Field(sa_column=Column(JSON))
    location: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    customer_id: int = Field(foreign_key="users.id")

    # relationships
    customer: "User" = Relationship()


class AddressCreate(SQLModel):
    title: str
    type: str
    address: Dict[str, Any]
    customer_id: int
    default: bool = False


class AddressRead(TimeStampReadModel):
    id: int
    title: str
    type: str
    default: bool


class AddressUpdate(SQLModel):
    title: Optional[str] = None
    type: Optional[str] = None
    default: Optional[bool] = None
