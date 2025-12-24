from typing import TYPE_CHECKING, List, Optional, Dict, Any
import datetime
from pydantic import BaseModel, EmailStr, model_validator,Field as PydanticField
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import JSON

from src.api.models.role_model.roleModel import RoleRead
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import (
        UserRole,
        Role,
        Shop,
        UserShop,
        UserMedia,
        Order,
        Address,
        Wishlist,
        Review,
        ReturnRequest,
        WalletTransaction,
        UserWallet,
        OrderReview
    )


class User(TimeStampedModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191)
    email: str = Field(max_length=191, index=True)
    phone_no: str = Field(max_length=30)
    is_root: bool = Field(default=False)
    email_verified_at: Optional[datetime.datetime] = None
    password: Optional[str] = None
    remember_token: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)
    password_reset_code: Optional[str] = Field(default=None, max_length=6)
    password_reset_code_expires: Optional[datetime.datetime] = None
    image: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    contactinfo: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    # contactinfo structure: {"name":"","father_name":"","cnic":"","employment_no":"","phoneno":"","address":"","email":""}
    # relationships
    user_roles: list["UserRole"] = Relationship(back_populates="user")
    media: List["UserMedia"] = Relationship(back_populates="user")
    shops: List["Shop"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "Shop.owner_id"},  # ✅ correct
    )
    user_shops: list["UserShop"] = Relationship(back_populates="user")
    #  order model
    customer_orders: List["Order"] = Relationship(
        back_populates="customer",
        sa_relationship_kwargs={
            "foreign_keys": "[Order.customer_id]"
        }
    )
    
    fullfillment_orders: List["Order"] = Relationship(
        back_populates="fullfillment_user",
        sa_relationship_kwargs={
            "foreign_keys": "[Order.fullfillment_id]"
        }
    )
    addresses: list["Address"] = Relationship(back_populates="customer")
    wishlists: Optional["Wishlist"] = Relationship(back_populates="user")
    reviews: Optional["Review"] = Relationship(back_populates="user")
    order_reviews: Optional["OrderReview"] = Relationship(back_populates="user")
    #return_requests: Optional["ReturnRequest"] = Relationship(back_populates="user")
    #wallet_transactions: Optional["WalletTransaction"] = Relationship(back_populates="user")
    #wallet: Optional["UserWallet"] = Relationship(back_populates="user")
    # As fulfillment user (user assigned to fulfill orders)
    # fulfillment_orders: List["Order"] = Relationship(
    #     back_populates="fulfillment_user",
    #     sa_relationship_kwargs={"foreign_keys": "Order.fullfillment_id"},
    # )

    @property
    def roles(self) -> list["Role"]:
        """Return Role objects directly"""
        return [ur.role for ur in self.user_roles if ur.role]

    @property
    def role_names(self) -> list[str]:
        return [role.name for role in self.roles]

    @property
    def permissions(self) -> list[str]:
        perms = []
        for role in self.roles:
            perms.extend(role.permissions)
        return perms


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

class UserCreate(SQLModel):
    name: str
    email: EmailStr
    phone_no: str
    password: str
    confirm_password: str
    role_ids: Optional[List[int]] = None  # Add role_ids for role assignment
    is_active: bool = True

    @model_validator(mode="before")
    def check_password_match(cls, values):
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values
    
class ShopReadForUser(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class UserReadBase(TimeStampReadModel):
    id: int
    name: str
    phone_no: str
    email: EmailStr
    is_active: bool
    is_root: bool
    image: Optional[Dict[str, Any]] = None
    contactinfo: Optional[Dict[str, Any]] = None

class UserRead(UserReadBase):
    roles: List[RoleRead] = None
    shops: List[ShopReadForUser] = None
    avatar: Optional[Dict[str, Any]] = None  # Computed avatar field

    class Config:
        from_attributes = True


class LoginRequest(SQLModel):
    email: EmailStr
    password: str

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone_no: Optional[str] = None
    image: Optional[Dict[str, Any]] = None
    contactinfo: Optional[Dict[str, Any]] = None

class UserUpdate(SQLModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_no: Optional[str] = None
    password: Optional[str] = None


class UpdateUserByAdmin(UserUpdate):
    # role_id: Optional[List] = None
    #role_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None
    contactinfo: Optional[Dict[str, Any]] = None

class ChangePasswordRequest(SQLModel):
    current_password: str
    new_password: str
    confirm_password: str

    @model_validator(mode="before")
    def check_password_match(cls, values):
        if values.get("new_password") != values.get("confirm_password"):
            raise ValueError("New passwords do not match")
        return values

class ForgotPasswordRequest(SQLModel):
    email: EmailStr

class VerifyCodeRequest(SQLModel):
    email: EmailStr
    verification_code: str = PydanticField(..., min_length=6, max_length=6)

class ResetPasswordRequest(SQLModel):
    email: EmailStr
    verification_code: str = PydanticField(..., min_length=6, max_length=6)
    new_password: str
    confirm_password: str

    @model_validator(mode="before")
    def check_password_match(cls, values):
        if values.get("new_password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values