# src/api/models/faqModel.py
from typing import Optional
from sqlmodel import SQLModel, Field
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


# --------------------------------------------------------------------
# MAIN MODEL
# --------------------------------------------------------------------
class FAQ(TimeStampedModel, table=True):
    __tablename__ = "faqs"

    id: Optional[int] = Field(default=None, primary_key=True)
    question: Optional[str] = None
    question_type: Optional[str] = None
    answer: Optional[str] = None
    order: int = Field(default=0, index=True)  # For manual ordering
    is_active: bool = Field(default=True, index=True)  # To show/hide FAQs

    class Config:
        arbitrary_types_allowed = True


# --------------------------------------------------------------------
# CRUD SCHEMAS
# --------------------------------------------------------------------
class FAQCreate(SQLModel):
    question: str
    question_type: str
    answer: str
    order: Optional[int] = 0
    is_active: Optional[bool] = True


class FAQRead(TimeStampReadModel):
    id: int
    question: str
    question_type: str
    answer: str
    order: int
    is_active: bool


class FAQUpdate(SQLModel):
    question: Optional[str] = None
    question_type: Optional[str] = None
    answer: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None