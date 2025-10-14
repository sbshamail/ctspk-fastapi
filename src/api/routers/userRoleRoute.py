from typing import Optional
from fastapi import (
    APIRouter,
    Query,
)
from sqlalchemy import select

from src.api.core.operation import listop
from src.api.core.security import hash_password
from src.api.core.dependencies import GetSession, requirePermission
from src.api.core.response import api_response, raiseExceptions
from src.api.models.usersModel import UpdateUserByAdmin, User, UserRead, UserUpdate
from src.api.models.role_model.roleModel import Role
from src.api.models.role_model.userRoleModel import UserRole

router = APIRouter(prefix="/user", tags=["User"])


@router.put("/update", response_model=UserRead)
def update_user(
    request: UserUpdate,
    session: GetSession,
    user=requirePermission("user-update"),
):
    user_id = user.get("id")
    db_user = session.get(User, user_id)
    raiseExceptions((db_user, 404, "User not found"))
    
    update_data = request.model_dump(exclude_unset=True)
    
    # Update basic fields
    for field, value in update_data.items():
        if value is not None and field != 'password':
            setattr(db_user, field, value)
    
    # Handle password update
    if request.password:
        hashed_password = hash_password(request.password)
        db_user.password = hashed_password
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return api_response(200, "User updated successfully", UserRead.model_validate(db_user))


@router.put("/updatebyadmin/{user_id}", response_model=UserRead)
def update_user_by_admin(
    user_id: int,
    request: UpdateUserByAdmin,
    session: GetSession,
    user=requirePermission("user-update"),
):
    db_user = session.get(User, user_id)
    raiseExceptions((db_user, 404, "User not found"))
    
    update_data = request.model_dump(exclude_unset=True)
    
    # Update basic fields
    for field, value in update_data.items():
        if value is not None and field != 'password':
            setattr(db_user, field, value)
    
    # Handle password update
    if request.password:
        hashed_password = hash_password(request.password)
        db_user.password = hashed_password
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return api_response(200, "User updated successfully", UserRead.model_validate(db_user))


@router.get("/read/{id}", response_model=UserRead)
def get_user(
    id: int,
    session: GetSession,
    user=requirePermission("user"),
):
    db_user = session.get(User, id)
    raiseExceptions((db_user, 404, "User not found"))
    return api_response(200, "User Found", UserRead.model_validate(db_user))


@router.delete("/delete/{id}")
def delete_user(
    id: int,
    session: GetSession,
    user=requirePermission("user-delete"),
):
    db_user = session.get(User, id)
    raiseExceptions((db_user, 404, "User not found"))

    session.delete(db_user)
    session.commit()
    return api_response(200, f"User {db_user.name} deleted successfully")


@router.patch("/{id}/status")
def update_user_status(
    id: int,
    is_active: bool,
    session: GetSession,
    user=requirePermission("user-update"),
):
    db_user = session.get(User, id)
    raiseExceptions((db_user, 404, "User not found"))

    db_user.is_active = is_active
    session.add(db_user)
    session.commit()

    action = "activated" if is_active else "deactivated"
    return api_response(200, f"User {action} successfully")


@router.get("/list", response_model=list[UserRead])
def list_users(
    session: GetSession,
    searchTerm: Optional[str] = None,
    role: Optional[str] = None,
    shop: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = None,
    skip: int = 0,
    limit: int = Query(200, ge=1, le=200),
    user=requirePermission("user"),
):
    filters = {
        "searchTerm": searchTerm,
        "columnFilters": []
    }

    # Add role filter
    if role:
        filters["columnFilters"].append(["user_roles.role.name", role])
    
    # Add shop filter
    if shop:
        filters["columnFilters"].append(["shops.name", shop])
    
    # Add active status filter
    if is_active is not None:
        filters["columnFilters"].append(["is_active", str(is_active)])

    searchFields = ["name", "email", "phone_no"]

    result = listop(
        session=session,
        Model=User,
        searchFields=searchFields,
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
        relationships=["user_roles.role", "shops", "media"]
    )

    if not result["data"]:
        return api_response(404, "No users found")

    users_data = [UserRead.model_validate(user) for user in result["data"]]
    return api_response(200, "Users found", users_data, result["total"])


@router.get("/profile", response_model=UserRead)
def get_user_profile(
    session: GetSession,
    user=requirePermission("user"),
):
    user_id = user.get("id")
    db_user = session.get(User, user_id)
    raiseExceptions((db_user, 404, "User not found"))
    return api_response(200, "User profile found", UserRead.model_validate(db_user))