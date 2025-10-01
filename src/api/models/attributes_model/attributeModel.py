from typing import TYPE_CHECKING, Literal, Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.attributes_model.attributeValueModel import AttributeValueRead
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


if TYPE_CHECKING:
    from src.api.models import AttributeValue


class Attribute(TimeStampedModel, table=True):
    __tablename__: Literal["attributes"] = "attributes"

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(max_length=191)
    language: str = Field(default="en", max_length=191)
    name: str = Field(max_length=191)

    # 📝 Example use: "Color", "Size", "Material"
    # One Attribute can have multiple AttributeValues (e.g. Color → Red, Blue, Green)

    # relationships
    values: List["AttributeValue"] = Relationship(back_populates="attribute")


class AttributeValueCreate(SQLModel):
    value: str
    meta: Optional[str] = None
    language: str = "en"


class AttributeCreate(SQLModel):
    name: str
    language: str = "en"
    shop_id: Optional[int] = None
    values: Optional[List[AttributeValueCreate]]


class AttributeRead(TimeStampReadModel):
    id: int
    slug: str
    name: str
    language: str
    values: Optional[List[AttributeValueRead]] = None


class AttributeUpdate(SQLModel):
    name: Optional[str] = None
    language: Optional[str] = None
