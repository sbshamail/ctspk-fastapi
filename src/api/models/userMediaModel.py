from typing import TYPE_CHECKING, Any, Dict, List, Optional
from pydantic import BaseModel, field_serializer, field_validator
from sqlalchemy import Column
from sqlmodel import JSON, SQLModel, Field, Relationship
from src.config import DOMAIN
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import User


class UserMedia(TimeStampedModel, table=True):
    __tablename__ = "media"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    media: Optional[List[Dict[str, Any]]] = Field(sa_column=Column(JSON))
    media_type: str  # "image" | "video" | "doc"
    # relationship back to user
    user: "User" = Relationship(back_populates="media")


class MediaItem(BaseModel):
    filename: Optional[str] = None
    extension: Optional[str] = None
    original: Optional[str] = None  # ✅ optional now
    size_mb: Optional[float] = None
    thumbnail: Optional[str] = None

    @field_serializer("original")
    def add_domain_to_url(self, v: Optional[str], _info):
        return f"{DOMAIN}{v}" if v else None

    @field_serializer("thumbnail")
    def add_domain_to_thumbnail(self, v: Optional[str], _info):
        return f"{DOMAIN}{v}" if v else None


# ✅ Base schema (shared between create/update)
class UserMediaBase(BaseModel):
    media_type: str
    media: List[MediaItem]  # array of items

    # ✅ Validator to check unique filename + orginal
    @field_validator("media")
    @classmethod
    def check_unique(cls, media_list: List[MediaItem]):
        filenames = set()
        urls = set()
        for item in media_list:
            if item.filename in filenames:
                raise ValueError(f"Duplicate filename detected: {item.filename}")
            if item.orginal in urls:
                raise ValueError(f"Duplicate URL detected: {item.orginal}")
            filenames.add(item.filename)
            urls.add(item.orginal)
        return media_list


# ✅ Create schema (add user_id)
class UserMediaCreate(UserMediaBase):
    user_id: int


class UserMediaRead(TimeStampReadModel):
    id: int
    media_type: Optional[str] = None
    media: Optional[list[MediaItem]] = None  # instead of single file

    class Config:
        from_attributes = True
