


from typing import Optional

from pydantic import Field
from sqlmodel import Relationship
from src.api.models.baseModel import TimeStampedModel


class UserRole(TimeStampedModel, table=True):
    __tablename__ = "user_roles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    role_id: int = Field(foreign_key="roles.id")
    
    # relationships
    user: "User" = Relationship(back_populates="user_roles")
    role: "Role" = Relationship(back_populates="user_roles")