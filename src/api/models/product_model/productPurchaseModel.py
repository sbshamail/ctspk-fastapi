# src/api/models/productPurchaseModel.py
from typing import TYPE_CHECKING, Literal, Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import Product


class ProductPurchase(TimeStampedModel, table=True):
    __tablename__: Literal["product_purchase"] = "product_purchase"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: Optional[int] = Field(foreign_key="products.id")
    quantity: Optional[int] = None
    purchase_date: Optional[datetime] = None
    price: Optional[float] = None
    sale_price: Optional[float] = None
    purchase_price: Optional[float] = None
    shop_id: int
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    # relationships
    product: Optional["Product"] = Relationship()


class ProductPurchaseCreate(SQLModel):
    product_id: Optional[int] = None
    quantity: int
    shop_id: int
    purchase_price: float


class ProductPurchaseRead(TimeStampReadModel):
    id: int
    product_id: Optional[int]
    quantity: int
    purchase_price: float


class ProductPurchaseVariationOption(TimeStampedModel, table=True):
    __tablename__: Literal["product_purchase_variation_options"] = (
        "product_purchase_variation_options"
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    product_purchase_id: int
    variation_options_id: Optional[int] = None
    price: float
    sale_price: Optional[float] = None
    purchase_price: Optional[float] = None
    language: str = Field(default="en", max_length=191)
    quantity: int
    sku: Optional[str] = Field(max_length=191)
    product_id: Optional[int] = Field(foreign_key="products.id")
    purchase_date: Optional[datetime] = None

    # relationships
    product: Optional["Product"] = Relationship()


class ProductPurchaseVariationOptionCreate(SQLModel):
    product_purchase_id: int
    price: float
    quantity: int
    product_id: Optional[int] = None


class ProductPurchaseVariationOptionRead(TimeStampReadModel):
    id: int
    product_purchase_id: int
    price: float
    quantity: int
