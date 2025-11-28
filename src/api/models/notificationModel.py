# src/api/models/notificationModel.py
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import User


class Notification(TimeStampedModel, table=True):
    __tablename__ = "notifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    message: str = Field(max_length=1000)  # Max 1000 characters
    is_read: bool = Field(default=False, index=True)
    read_at: Optional[datetime] = Field(default=None)  # When notification was read
    sent_at: datetime = Field(default_factory=datetime.utcnow, index=True)  # When notification was sent

    # Relationship
    user: Optional["User"] = Relationship()

    class Config:
        arbitrary_types_allowed = True


# --------------------------------------------------------------------
# CRUD SCHEMAS
# --------------------------------------------------------------------
class NotificationCreate(SQLModel):
    user_id: int
    message: str = Field(max_length=1000)


class NotificationUpdate(SQLModel):
    message: Optional[str] = Field(default=None, max_length=1000)


class NotificationRead(TimeStampReadModel):
    id: int
    user_id: int
    message: str
    is_read: bool
    read_at: Optional[datetime] = None
    sent_at: datetime


class NotificationMarkAsRead(SQLModel):
    """Schema for marking notification as read"""
    pass  # No fields needed, just triggers the action


class NotificationBulkMarkAsRead(SQLModel):
    """Schema for marking multiple notifications as read"""
    notification_ids: list[int]
