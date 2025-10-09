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
    options: Dict[str, Any] = Field(sa_column=Column(JSON))
    product_id: Optional[int] = Field(foreign_key="products.id")
    is_digital: bool = Field(default=False)

    # relationships
    product: "Product" = Relationship(back_populates="variation_options")
    wishlists: Optional["Wishlist"] = Relationship(back_populates="variation_option")
    reviews: Optional["Review"] = Relationship(back_populates="variation_option")
class VariationOptionCreate(SQLModel):
    title: str
    price: str
    quantity: int
    product_id: int
    options: Dict[str, Any]


class VariationOptionRead(TimeStampReadModel):
    id: int
    title: str
    price: str
    quantity: int
    product_id: int


class VariationOptionUpdate(SQLModel):
    title: Optional[str] = None
    price: Optional[str] = None
    quantity: Optional[int] = None
