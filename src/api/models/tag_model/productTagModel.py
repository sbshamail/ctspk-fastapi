# src/api/models/productTagModel.py
from typing import TYPE_CHECKING, Literal, Optional
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import Product, Tag


class ProductTag(SQLModel, table=True):
    __tablename__: Literal["product_tag"] = "product_tag"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id")
    tag_id: int = Field(foreign_key="tags.id")

    # relationships
    product: "Product" = Relationship(back_populates="tags")
    tag: "Tag" = Relationship(back_populates="products")


class ProductTagCreate(SQLModel):
    product_id: int
    tag_id: int


class ProductTagRead(SQLModel):
    id: int
    product_id: int
    tag_id: int
