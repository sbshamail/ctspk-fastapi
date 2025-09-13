# src/api/models/typeModel.py
from typing import Literal, Optional, Dict, Any
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


class Type(TimeStampedModel, table=True):
    __tablename__: Literal["types"] = "types"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191)
    settings: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    slug: str = Field(max_length=191)
    language: str = Field(default="en", max_length=191)
    icon: Optional[str] = Field(max_length=191)
    is_active: bool = Field(default=True)
    promotional_sliders: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))


class TypeCreate(SQLModel):
    name: str
    slug: str
    is_active: bool = True


class TypeRead(TimeStampReadModel):
    id: int
    name: str
    slug: str
    is_active: bool


class TypeUpdate(SQLModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
