# src/api/models/contactusModel.py
from typing import Optional
from sqlmodel import SQLModel, Field
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


# --------------------------------------------------------------------
# MAIN MODEL
# --------------------------------------------------------------------
class ContactUs(TimeStampedModel, table=True):
    __tablename__ = "contactus"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(index=True)
    subject: str
    message: str
    category: Optional[str] = None  # Only for /support endpoint
    is_processed: bool = Field(default=False, index=True)  # To track if support has responded
    notes: Optional[str] = None  # For internal notes by support team

    class Config:
        arbitrary_types_allowed = True


# --------------------------------------------------------------------
# CRUD SCHEMAS
# --------------------------------------------------------------------
class ContactUsSupportCreate(SQLModel):
    """Schema for /contactus/support endpoint with category"""
    name: str
    email: str
    subject: str
    message: str
    category: str


class ContactUsSendCreate(SQLModel):
    """Schema for /contactus/send endpoint without category"""
    name: str
    email: str
    subject: str
    message: str


class ContactUsRead(TimeStampReadModel):
    id: int
    name: str
    email: str
    subject: str
    message: str
    category: Optional[str] = None
    is_processed: bool
    notes: Optional[str] = None


class ContactUsUpdate(SQLModel):
    """For admin to update status and notes"""
    is_processed: Optional[bool] = None
    notes: Optional[str] = None
