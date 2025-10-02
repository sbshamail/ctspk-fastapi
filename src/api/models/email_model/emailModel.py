from typing import Literal, Optional
from sqlalchemy import Column, Enum,Index
from datetime import datetime
from sqlmodel import SQLModel, Field
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel
from enum import Enum as PyEnum





class Emailtemplate(TimeStampedModel, table=True):
    __tablename__: Literal["email_template"] = "email_template"

    # Use mapper arguments to handle the conflict
    __mapper_args__ = {"column_prefix": "_"}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191, nullable=False)
    slug: str = Field(max_length=191, index=True, unique=True)  # ✅ indexed + unique
    subject: str = Field(max_length=300, nullable=False)
    content: Optional[str] = None
    is_active: bool = Field(default=True)
    language: str = Field(default="en", max_length=191)
    
    __table_args__ = (
        Index("ix_emails_slug", "slug", unique=True),
    )


class EmailCreate(SQLModel):
    name: str
    subject: Optional[str] = None
    content: Optional[str] = None
    is_active: bool = True

class EmailRead(TimeStampReadModel):
    name: str
    amount: float
    content: Optional[str]
    is_active: bool 

class EmailActivate(SQLModel):
    is_active: bool

class EmailUpdate(SQLModel):
    name: str
    subject: Optional[str] = None
    content: Optional[str] = None
    is_active: bool = True