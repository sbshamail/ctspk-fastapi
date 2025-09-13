# src/api/models/tagModel.py
from typing import TYPE_CHECKING, Literal, Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import Type, ProductTag


class Tag(TimeStampedModel, table=True):
    __tablename__: Literal["tags"] = "tags"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191)
    slug: str = Field(max_length=191)
    language: str = Field(default="en", max_length=191)
    icon: Optional[str] = Field(max_length=191)
    image: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    details: Optional[str] = None
    type_id: int = Field(foreign_key="types.id")
    deleted_at: Optional[datetime] = None

    # relationships
    type: "Type" = Relationship()
    products: List["ProductTag"] = Relationship(back_populates="tag")


class TagCreate(SQLModel):
    name: str
    slug: str
    type_id: int


class TagRead(TimeStampReadModel):
    id: int
    name: str
    slug: str


class TagUpdate(SQLModel):
    name: Optional[str] = None
    slug: Optional[str] = None
