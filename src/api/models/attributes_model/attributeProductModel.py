from typing import TYPE_CHECKING, Literal, Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import AttributeValue, Product


class AttributeProduct(TimeStampedModel, table=True):
    __tablename__: Literal["attribute_product"] = "attribute_product"

    id: Optional[int] = Field(default=None, primary_key=True)
    # foreign key
    attribute_value_id: int = Field(foreign_key="attribute_values.id")
    product_id: int = Field(foreign_key="products.id")

    # 📝 Join table: connects products to specific attribute values.
    # Example: Product #42 → Attribute "Color" → Value "Red"
    attribute_value: "AttributeValue" = Relationship(
        back_populates="attributes_products"
    )
    product: "Product" = Relationship(back_populates="attributes")


class AttributeProductCreate(SQLModel):
    attribute_value_id: int
    product_id: int


class AttributeProductRead(TimeStampReadModel):
    id: int
    attribute_value_id: int
    product_id: int


class AttributeProductUpdate(SQLModel):
    attribute_value_id: Optional[int] = None
    product_id: Optional[int] = None
