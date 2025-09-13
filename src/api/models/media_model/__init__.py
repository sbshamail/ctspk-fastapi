# src/api/models/mediaModel.py
from typing import Literal, Optional, Dict, Any
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


class Media(TimeStampedModel, table=True):
    __tablename__: Literal["media"] = "media"

    id: Optional[int] = Field(default=None, primary_key=True)
    type_model: str = Field(max_length=191)
    modelid: int
    uuid: Optional[str] = Field(max_length=36)
    collection_name: str = Field(max_length=191)
    name: str = Field(max_length=191)
    file_name: str = Field(max_length=191)
    mime_type: Optional[str] = Field(max_length=191)
    disk: str = Field(max_length=191)
    conversions_disk: Optional[str] = Field(max_length=191)
    size: int
    manipulations: Dict[str, Any] = Field(sa_column=Column(JSON))
    generated_conversions: Dict[str, Any] = Field(sa_column=Column(JSON))
    custom_properties: Dict[str, Any] = Field(sa_column=Column(JSON))
    responsive_images: Dict[str, Any] = Field(sa_column=Column(JSON))
    order_column: Optional[int] = None


class MediaCreate(SQLModel):
    type_model: str
    modelid: int
    collection_name: str
    name: str
    file_name: str
    disk: str
    size: int


class MediaRead(TimeStampReadModel):
    id: int
    type_model: str
    modelid: int
    name: str
    file_name: str


class MediaUpdate(SQLModel):
    name: Optional[str] = None
    order_column: Optional[int] = None
