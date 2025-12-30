# src/api/models/addressModel.py
from typing import TYPE_CHECKING, Literal,Optional, List
from datetime import datetime
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel, Field as PydanticField
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import User

# --------------------------------------------------------------------
# Pydantic sub-models for JSON validation
# --------------------------------------------------------------------

class AddressDetail(BaseModel):
    street: str = PydanticField(..., max_length=191)
    city: str = PydanticField(..., max_length=191)
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

class Location(BaseModel):
    lat: Optional[float] = None  # Make optional
    lng: Optional[float] = None  # Make optional
# --------------------------------------------------------------------
# SQLModel Table
# --------------------------------------------------------------------

class Address(TimeStampedModel, table=True):
    __tablename__ = "address"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=191)
    type: str = Field(max_length=191)
    is_default: bool = Field(default=False)

    address: AddressDetail = Field(sa_column=Column(JSON))
    location: Optional[Location] = Field(default=None,sa_column=Column(JSON))

    customer_id: int = Field(foreign_key="users.id")

    # relationships
    customer: "User" = Relationship(back_populates="addresses")

# --------------------------------------------------------------------
# CRUD Schemas
# --------------------------------------------------------------------

class AddressCreate(SQLModel):
    title: str
    type: str
    address: AddressDetail
    customer_id: Optional[int] = None  # Optional - set from authenticated user's token
    is_default: bool = False
    location: Optional[Location] = None

class AddressRead(TimeStampReadModel):
    id: int
    title: str
    type: str
    is_default: bool
    address: AddressDetail
    location: Optional[Location]

class AddressUpdate(SQLModel):
    title: Optional[str] = None
    type: Optional[str] = None
    is_default: Optional[bool] = None
    address: Optional[AddressDetail] = None
    location: Optional[Location] = None
