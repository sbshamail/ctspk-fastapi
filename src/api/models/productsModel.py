# src/api/models/productModel.py
from typing import Optional, List
import datetime
from sqlmodel import SQLModel, Field, Relationship

from src.api.models.baseModel import TimeStampedModel


class Product(TimeStampedModel, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191)
    slug: str = Field(max_length=191)
    description: Optional[str] = None

    price: Optional[float] = None

    sale_price: Optional[float] = None
    purchase_price: Optional[float] = None
    language: str = Field(default="en", max_length=191)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sku: Optional[str] = None
    bar_code: Optional[str] = None
    quantity: int = Field(default=0)
    in_stock: bool = Field(default=True)
    is_taxable: bool = Field(default=False)

    status: str = Field(default="publish")  # enum in SQL
    product_type: str = Field(default="simple")  # enum in SQL
    unit: str = Field(max_length=191)
    height: Optional[str] = None
    width: Optional[str] = None
    length: Optional[str] = None
    image: Optional[dict] = None
    video: Optional[dict] = None
    gallery: Optional[dict] = None
    deleted_at: Optional[datetime.datetime] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    is_digital: bool = Field(default=False)
    is_external: bool = Field(default=False)
    external_product_url: Optional[str] = None
    external_product_button_text: Optional[str] = None
    # foreign_key
    author_id: Optional[int] = Field(default=None, foreign_key="authors.id")
    manufacturer_id: Optional[int] = Field(default=None, foreign_key="manufacturers.id")
    shop_id: Optional[int] = Field(default=None, foreign_key="shops.id")
    type_id: int = Field(foreign_key="types.id")
    shipping_class_id: Optional[int] = Field(
        default=None, foreign_key="shipping_classes.id"
    )
    # relationships
    shop: Optional["Shop"] = Relationship(back_populates="products")
    wishlists: List["Wishlist"] = Relationship(back_populates="product")
