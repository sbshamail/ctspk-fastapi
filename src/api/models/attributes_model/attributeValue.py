from typing import TYPE_CHECKING, Literal, Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import AttributeProduct, Attribute


class AttributeValue(TimeStampedModel, table=True):
    __tablename__: Literal["attribute_values"] = "attribute_values"

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(max_length=191)
    attribute_id: int = Field(foreign_key="attributes.id")
    value: str = Field(max_length=191)
    language: str = Field(default="en", max_length=191)
    meta: Optional[str] = Field(max_length=191)

    # relationships
    attribute: "Attribute" = Relationship(back_populates="values")
    attributes_products: List["AttributeProduct"] = Relationship(
        back_populates="attribute_value"
    )


class AttributeValueCreate(SQLModel):
    slug: str
    attribute_id: int
    value: str
    language: str = "en"


class AttributeValueRead(TimeStampReadModel):
    id: int
    slug: str
    value: str
    language: str


class AttributeValueUpdate(SQLModel):
    value: Optional[str] = None
    language: Optional[str] = None
