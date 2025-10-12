# src/api/models/variationOptionModel.py
from typing import TYPE_CHECKING, Literal, Optional, Dict, Any
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import Product,Wishlist,Review


class VariationOption(TimeStampedModel, table=True):
    __tablename__: Literal["variation_options"] = "variation_options"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=191)
    image: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    price: str = Field(max_length=191)
    sale_price: Optional[str] = Field(max_length=191)
    purchase_price: Optional[float] = None
    language: str = Field(default="en", max_length=191)
    quantity: int
    is_disable: bool = Field(default=False)
    sku: Optional[str] = Field(max_length=191)
    bar_code: Optional[str] = Field(max_length=250)  # ADDED: Barcode for variations
    options: Dict[str, Any] = Field(sa_column=Column(JSON))
    product_id: Optional[int] = Field(foreign_key="products.id")
    is_digital: bool = Field(default=False)
    is_active: bool = Field(default=True)  # ADDED: Active status for variations

    # relationships
    product: "Product" = Relationship(back_populates="variation_options")
    wishlists: Optional["Wishlist"] = Relationship(back_populates="variation_option")
    reviews: Optional["Review"] = Relationship(back_populates="variation_option")


class VariationOptionCreate(SQLModel):
    title: str
    price: str
    sale_price: Optional[str] = None
    purchase_price: Optional[float] = None
    quantity: int
    product_id: int
    options: Dict[str, Any]
    image: Optional[Dict[str, Any]] = None
    sku: Optional[str] = None
    bar_code: Optional[str] = None
    is_active: bool = True


class VariationOptionRead(TimeStampReadModel):
    id: int
    title: str
    price: str
    sale_price: Optional[str] = None
    purchase_price: Optional[float] = None
    quantity: int
    product_id: int
    options: Dict[str, Any]
    image: Optional[Dict[str, Any]] = None
    sku: Optional[str] = None
    bar_code: Optional[str] = None
    is_active: bool


class VariationOptionUpdate(SQLModel):
    title: Optional[str] = None
    price: Optional[str] = None
    sale_price: Optional[str] = None
    purchase_price: Optional[float] = None
    quantity: Optional[int] = None
    options: Optional[Dict[str, Any]] = None
    image: Optional[Dict[str, Any]] = None
    sku: Optional[str] = None
    bar_code: Optional[str] = None
    is_active: Optional[bool] = None