from typing import TYPE_CHECKING, Literal, Optional


from sqlmodel import Field, Relationship
from src.api.models.baseModel import TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import User, Role


class UserRole(TimeStampedModel, table=True):
    __tablename__: Literal["user_roles"] = "user_roles"

    id: Optional[int] = Field(default=None, primary_key=True)  # type: ignore
    user_id: int = Field(foreign_key="users.id")
    role_id: int = Field(foreign_key="roles.id")

    # relationships
    user: "User" = Relationship(back_populates="user_roles")
    role: "Role" = Relationship(back_populates="user_roles")
