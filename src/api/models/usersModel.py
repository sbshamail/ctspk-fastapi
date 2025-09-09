# src/api/models/userModel.py
from typing import Optional, List
import datetime
from pydantic import EmailStr, model_validator
from sqlalchemy import Column, ForeignKey
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


class User(TimeStampedModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191)
    email: str = Field(max_length=191, index=True)
    email_verified_at: Optional[datetime.datetime] = None
    password: Optional[str] = None
    remember_token: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)

    shop_id: Optional[int] = Field(
        sa_column=Column(
            ForeignKey("shops.id", use_alter=True, name="fk_users_shop_id"),
            nullable=True,
        )
    )
    role_id: Optional[int] = Field(default=None, foreign_key="roles.id")

    # relationships
    role: Optional["Role"] = Relationship(back_populates="users")
    shops: List["Shop"] = Relationship(back_populates="owner")
    # profile: Optional["UserProfile"] = Relationship(back_populates="user")
    # wallets: List["Wallet"] = Relationship(back_populates="user")
    # addresses: List["Address"] = Relationship(back_populates="user")
    # wishlists: List["Wishlist"] = Relationship(back_populates="user")


class RegisterUser(SQLModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: str

    @model_validator(mode="before")
    def check_password_match(cls, values):
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values
