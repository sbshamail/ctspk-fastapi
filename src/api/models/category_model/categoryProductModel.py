# src/api/models/categoryProductModel.py
from typing import TYPE_CHECKING, Literal, Optional
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import Product, Category


class CategoryProduct(TimeStampedModel, table=True):
    __tablename__: Literal["category_product"] = "category_product"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id")
    category_id: int = Field(foreign_key="categories.id")
    admin_commission_rate: float = Field(default=0)

    # relationships
    product: "Product" = Relationship(back_populates="categories")
    category: "Category" = Relationship(back_populates="products")


class CategoryProductCreate(SQLModel):
    product_id: int
    category_id: int
    admin_commission_rate: float = 0


class CategoryProductRead(SQLModel):
    id: int
    product_id: int
    category_id: int
    admin_commission_rate: float
