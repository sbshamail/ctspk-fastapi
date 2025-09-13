from typing import TYPE_CHECKING, Literal, Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import AttributeValue, Product


class AttributeProduct(TimeStampedModel, table=True):
    __tablename__: Literal["attribute_product"] = "attribute_product"

    id: Optional[int] = Field(default=None, primary_key=True)
    attribute_value_id: int = Field(foreign_key="attribute_values.id")
    product_id: int = Field(foreign_key="products.id")

    # relationships
    attribute_value: "AttributeValue" = Relationship(back_populates="products")
    product: "Product" = Relationship(back_populates="attributes")


class AttributeProductCreate(SQLModel):
    attribute_value_id: int
    product_id: int


class AttributeProductRead(TimeStampReadModel):
    id: int
    attribute_value_id: int
    product_id: int
