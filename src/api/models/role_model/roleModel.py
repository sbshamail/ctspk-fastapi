from typing import List, Optional
from sqlalchemy import JSON
from sqlmodel import Field, Relationship, SQLModel

from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


class Role(TimeStampedModel, table=True):
    __tablename__ = "roles"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, unique=True)
    description: Optional[str] = None
    permissions: list[str] = Field(
        default_factory=list,
        sa_type=JSON,
    )
    is_active: bool = Field(default=True)
   # relationships
    user_roles: List["UserRole"] = Relationship(back_populates="role")


class RoleRead(TimeStampReadModel):
    id: int
    title: str
    permissions: list[str]


class RoleCreate(SQLModel):
    title: str
    permissions: list[str]


class RoleUpdate(SQLModel):
    title: Optional[str]
    permissions: Optional[list[str]]
