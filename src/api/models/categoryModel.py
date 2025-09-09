# src/api/models/categoryModel.py
from typing import Optional
import datetime
from sqlmodel import SQLModel, Field

from src.api.models.baseModel import TimeStampedModel


class Category(TimeStampedModel, table=True):
    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191)
    slug: str = Field(max_length=191)
    language: str = Field(default="en", max_length=191)
    icon: Optional[str] = None
    image: Optional[dict] = None
    details: Optional[str] = None
    parent: Optional[int] = Field(default=None, foreign_key="categories.id")
    type_id: int = Field(foreign_key="types.id")
    admin_commission_rate: Optional[float] = None
    is_active: bool = Field(default=True)
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    deleted_at: Optional[datetime.datetime] = None
