# src/api/models/userModel.py
from __future__ import annotations
from typing import Literal, Optional, List, TYPE_CHECKING
import datetime
from pydantic import EmailStr, model_validator
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import UserRole, Shop, Order


class User(TimeStampedModel, table=True):
    __tablename__: Literal["users"] = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191)
    email: str = Field(max_length=191, index=True)
    phone_no: str = Field(max_length=30)
    email_verified_at: Optional[datetime.datetime] = None
    password: Optional[str] = None
    remember_token: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)

    # relationships
    user_roles: List["UserRole"] = Relationship(back_populates="user")
    shops: List["Shop"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "Shop.owner_id"},  # ✅ correct
    )
    # As fulfillment user (user assigned to fulfill orders)
    fulfillment_orders: List["Order"] = Relationship(
        back_populates="fulfillment_user",
        sa_relationship_kwargs={"foreign_keys": "Order.fullfillment_id"},
    )


class RegisterUser(SQLModel):
    name: str
    email: EmailStr
    phone_no: str
    password: str
    confirm_password: str

    @model_validator(mode="before")
    def check_password_match(cls, values):
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values


class UserReadBase(TimeStampReadModel):
    id: int
    name: str
    phone_no: str
    email: EmailStr
    is_active: bool


# class UserRead(UserReadBase):
#     role: Optional[RoleRead] = None


class LoginRequest(SQLModel):
    email: EmailStr
    password: str


class UserUpdate(SQLModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_no: Optional[str] = None
    password: Optional[str] = None


class UpdateUserByAdmin(UserUpdate):
    # role_id: Optional[List] = None
    is_active: Optional[bool] = None
