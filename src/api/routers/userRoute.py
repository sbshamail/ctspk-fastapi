from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Request,
)
from sqlalchemy import select

from src.api.core.operation import listop

from src.api.core.security import hash_password
from src.api.core import updateOp, requireSignin
from src.api.core.dependencies import GetSession, requirePermission, requireAdmin
from src.api.core.response import api_response, raiseExceptions
from src.api.models.usersModel import UserCreate,RegisterUser, UpdateUserByAdmin, User, UserRead, UserUpdate
from src.api.models.role_model.roleModel import Role
from src.api.models.role_model.userRoleModel import UserRole

router = APIRouter(prefix="/user", tags=["user"])

@router.post("/create")
def create_user(
    request: UserCreate,
    session: GetSession,
    user=requirePermission("system:*"),
):
    # Check if user already exists
    existing_user = session.exec(
        select(User).where(User.email == request.email)
    ).first()
    if existing_user:
        return api_response(400, "User with this email already exists")

    # Hash password
    hashed_password = hash_password(request.password)
    
    # Create user data (exclude role_ids and confirm_password)
    user_data = request.model_dump(exclude={'password', 'confirm_password', 'role_ids'})
    user_data['password'] = hashed_password
    
    # Create user
    new_user = User(**user_data)
    session.add(new_user)
    session.flush()  # Flush to get the new user ID without committing

    # Assign roles if role_ids are provided
    if request.role_ids:
        for role_id in request.role_ids:
            # Check if role exists
            role = session.get(Role, role_id)
            if not role:
                session.rollback()
                return api_response(404, f"Role with ID {role_id} not found")
            
            # Check if user-role relationship already exists
            existing_user_role = session.exec(
                select(UserRole).where(
                    UserRole.user_id == new_user.id,
                    UserRole.role_id == role_id
                )
            ).first()
            
            if not existing_user_role:
                user_role = UserRole(user_id=new_user.id, role_id=role_id)
                session.add(user_role)

    session.commit()
    session.refresh(new_user)

    return api_response(201, "User created successfully", UserRead.model_validate(new_user))
@router.put("/update", response_model=UserRead)
def update_user(
    user: requireSignin,
    request: UserUpdate,
    session: GetSession,
):
    user_id = user.get("id")
    db_user = session.get(User, user_id)  # Like findById
    raiseExceptions((db_user, 404, "User not found"))
    update_user = updateOp(db_user, request, session)
    if request.password:
        hashed_password = hash_password(request.password)
        update_user.password = hashed_password
    session.commit()
    session.refresh(db_user)
    return api_response(200, "User Found", UserRead.model_validate(db_user))


@router.put("/updatebyadmin/{user_id}", response_model=UserRead)
def update_user_by_admin(
    user_id: int,
    request: UpdateUserByAdmin,  # You might want to create a UserUpdateWithRoles schema
    session: GetSession,
    user=requirePermission("all"),
):
    db_user = session.get(User, user_id)
    raiseExceptions((db_user, 404, "User not found"))
    
    update_data = request.model_dump(exclude_unset=True, exclude={'role_ids'})
    
    # Update basic fields
    for field, value in update_data.items():
        if value is not None and field != 'password':
            setattr(db_user, field, value)
    
    # Handle password update
    if request.password:
        hashed_password = hash_password(request.password)
        db_user.password = hashed_password
    
    # Handle role assignments if role_ids are provided
    if hasattr(request, 'role_ids') and request.role_ids is not None:
        # Remove existing user roles
        existing_user_roles = session.exec(
            select(UserRole).where(UserRole.user_id == user_id)
        ).all()
        for user_role in existing_user_roles:
            session.delete(user_role)
        
        # Add new user roles
        for role_id in request.role_ids:
            role = session.get(Role, role_id)
            if role:
                user_role = UserRole(user_id=user_id, role_id=role_id)
                session.add(user_role)
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return api_response(200, "User updated successfully", UserRead.model_validate(db_user))

@router.get("/read", response_model=UserRead)
def get_user(
    user: requireSignin,
    session: GetSession,
):
    user_id = user.get("id")
    db_user = session.get(User, user_id)  # Like findById
    raiseExceptions((db_user, 400, "User not found"))
    read = UserRead.model_validate(db_user)
    return api_response(200, "User Found", read)


# ✅ DELETE
@router.delete("/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    session: GetSession,
    user=requirePermission("all"),
):
    db_user = session.get(User, user_id)
    raiseExceptions((db_user, 400, "User not found"))

    session.delete(db_user)
    session.commit()
    return api_response(404, f"User {user_id} deleted")


# ✅ READ ALL
@router.get("/list", response_model=list[UserRead])  # no response_model
def list_users(
    user: requireAdmin,
    session: GetSession,
    dateRange: Optional[
        str
    ] = None,  # JSON string like '["created_at", "01-01-2025", "01-12-2025"]'
    numberRange: Optional[str] = None,  # JSON string like '["amount", "0", "100000"]'
    searchTerm: str = None,
    columnFilters: Optional[str] = Query(
        None
    ),  # e.g. '[["name","car"],["description","product"]]'
    page: int = None,
    skip: int = 0,
    limit: int = Query(10, ge=1, le=200),
):

    filters = {
        "searchTerm": searchTerm,
        "columnFilters": columnFilters,
        "dateRange": dateRange,
        "numberRange": numberRange,
        # "customFilters": customFilters,
    }

    searchFields = [
        "name",
        "email",
        "roles.name",
    ]
    result = listop(
        session=session,
        Model=User,
        searchFields=searchFields,
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
    )
    if not result["data"]:
        return api_response(404, "No User found")
    data = [UserRead.model_validate(prod) for prod in result["data"]]

    return api_response(
        200,
        "User found",
        data,
        result["total"],
    )
