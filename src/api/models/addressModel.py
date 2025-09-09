# src/api/models/addressModel.py
from typing import Optional
import datetime
from sqlmodel import SQLModel, Field, Relationship

from src.api.models.baseModel import TimeStampedModel


class Address(TimeStampedModel, table=True):
    __tablename__ = "address"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=191)
    type: str = Field(max_length=191)
    default: bool = Field(default=False)
    address: dict
    location: Optional[dict] = None
    customer_id: int = Field(foreign_key="users.id")
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    user: "User" = Relationship(back_populates="addresses")
