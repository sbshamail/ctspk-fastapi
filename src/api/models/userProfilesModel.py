# src/api/models/userProfileModel.py
from typing import Optional
import datetime
from sqlmodel import SQLModel, Field, Relationship

from src.api.models.baseModel import TimeStampedModel


class UserProfile(TimeStampedModel, table=True):
    __tablename__ = "user_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    avatar: Optional[dict] = None
    bio: Optional[str] = None
    socials: Optional[dict] = None
    contact: Optional[str] = None
    notifications: Optional[dict] = None
    customer_id: int = Field(foreign_key="users.id")
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    user: "User" = Relationship(back_populates="profile")
