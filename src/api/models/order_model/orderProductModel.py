# src/api/models/orderProductModel.py
from typing import TYPE_CHECKING, Literal, Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import Order, Product, VariationOption


class OrderProduct(TimeStampedModel, table=True):
    __tablename__: Literal["order_product"] = "order_product"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    product_id: int = Field(foreign_key="products.id")
    variation_option_id: Optional[int] = Field(foreign_key="variation_options.id")
    order_quantity: str = Field(max_length=191)
    unit_price: float
    subtotal: float
    admin_commission: float = Field(default=0.00)
    deleted_at: Optional[datetime] = None

    # relationships
    order: "Order" = Relationship(back_populates="order_products")
    product: "Product" = Relationship(back_populates="order_products")
    variation_option: Optional["VariationOption"] = Relationship()


class OrderProductCreate(SQLModel):
    order_id: int
    product_id: int
    order_quantity: str
    unit_price: float
    subtotal: float


class OrderProductRead(TimeStampReadModel):
    id: int
    order_id: int
    product_id: int
    order_quantity: str
    unit_price: float
    subtotal: float
