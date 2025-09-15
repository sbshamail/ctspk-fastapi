from typing import Optional

from pydantic import BaseModel
from src.api.models.role_model.roleModel import RoleRead

from src.api.models.usersModel import UserReadBase


# Circular import  issue we define seperately
class UserRoleRead(BaseModel):
    id: int
    user_id: int
    role_id: int
    user: Optional[UserReadBase] = None
    role: Optional[RoleRead] = None

    model_config = {"from_attributes": True}  # allows SQLModel/ORM instances
