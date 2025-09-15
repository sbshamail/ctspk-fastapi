from typing import TYPE_CHECKING, Optional
from sqlalchemy import JSON
from sqlmodel import Field, Relationship, SQLModel

from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


if TYPE_CHECKING:
    from src.api.models import UserRole


class Role(TimeStampedModel, table=True):
    __tablename__ = "roles"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50)
    description: Optional[str] = None
    permissions: list[str] = Field(
        default_factory=list,
        sa_type=JSON,
    )
    user_id: int = Field(foreign_key="users.id")
    is_active: bool = Field(default=True)
    # relationships
    user_roles: list["UserRole"] = Relationship(back_populates="role")

    @property
    def roles(self):
        """Return roles directly (not UserRole objects)."""
        return [ur.role for ur in self.user_roles if ur.role]


class RoleReadBase(TimeStampReadModel):
    id: int
    name: str
    permissions: list[str]
    user_id: int


class RoleRead(RoleReadBase):
    """Full role info returned in UserRead"""

    pass


class RoleCreate(SQLModel):
    name: str
    permissions: list[str]


class RoleUpdate(SQLModel):
    title: Optional[str]
    permissions: Optional[list[str]]
