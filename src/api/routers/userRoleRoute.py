from typing import Optional, List
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
    user=requirePermission("user:delete"),
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
    role: Optional[str] = Query(None, description="Filter by role name (legacy)"),
    shop: Optional[str] = None,
    is_active: Optional[bool] = None,
    role_ids: Optional[List[int]] = Query(None, description="Filter by allowed role IDs (include users with these roles)"),
    exclude_role_ids: Optional[List[int]] = Query(None, description="Filter by excluded role IDs (exclude users with these roles)"),
    customer: Optional[bool] = Query(None, description="If true, show only users without any roles (customers)"),
    page: int = None,
    skip: int = 0,
    limit: int = Query(200, ge=1, le=200),
    user=requirePermission("user"),
):
    """
    List users with role filtering options:
    - role: Filter by role name (legacy support)
    - role_ids: Include users with ANY of these role IDs (allowed roles)
    - exclude_role_ids: Exclude users with ANY of these role IDs (not allowed roles)
    - customer: If true, show only users without any roles (customers)

    Examples:
    - /user/list?role_ids=1&role_ids=2 - Get users with role 1 OR role 2
    - /user/list?exclude_role_ids=3&exclude_role_ids=4 - Get users WITHOUT role 3 AND role 4
    - /user/list?role_ids=1&role_ids=2&exclude_role_ids=3 - Get users with role 1 or 2, but NOT role 3
    - /user/list?customer=true - Get users without any roles (customers only)
    """
    from sqlalchemy import select as sa_select, distinct
    from sqlmodel import select as sm_select

    filters = {
        "searchTerm": searchTerm,
        "columnFilters": []
    }

    # Add role filter by name (legacy)
    if role:
        filters["columnFilters"].append(["user_roles.role.name", role])

    # Add shop filter
    if shop:
        filters["columnFilters"].append(["shops.name", shop])

    # Add active status filter
    if is_active is not None:
        filters["columnFilters"].append(["is_active", str(is_active)])

    searchFields = ["name", "email", "phone_no"]

    # Build base statement - will be modified if role filtering is needed
    base_statement = None

    # Get all user IDs that have at least one role
    users_with_roles_query = sa_select(distinct(UserRole.user_id))
    users_with_roles = [row[0] for row in session.execute(users_with_roles_query).fetchall()]

    # Handle customer filter - show only users without any roles
    if customer is True:
        # Get all users and exclude those with roles
        all_users_query = sa_select(distinct(User.id))
        all_user_ids = [row[0] for row in session.execute(all_users_query).fetchall()]
        customer_user_ids = [uid for uid in all_user_ids if uid not in users_with_roles]

        if not customer_user_ids:
            return api_response(404, "No customers found")

        base_statement = sm_select(User).where(User.id.in_(customer_user_ids))

    # Handle role_ids and exclude_role_ids filtering
    elif role_ids or exclude_role_ids:
        # Get user IDs that match the role criteria
        if role_ids:
            # Get users who have ANY of the allowed role_ids
            included_user_ids_query = (
                sa_select(distinct(UserRole.user_id))
                .where(UserRole.role_id.in_(role_ids))
            )
            included_user_ids = [row[0] for row in session.execute(included_user_ids_query).fetchall()]
        else:
            # When exclude_role_ids is used without role_ids, start with users who have roles
            # (users without roles should not be shown when role filter is applied)
            included_user_ids = users_with_roles

        if exclude_role_ids:
            # Get users who have ANY of the excluded role_ids
            excluded_user_ids_query = (
                sa_select(distinct(UserRole.user_id))
                .where(UserRole.role_id.in_(exclude_role_ids))
            )
            excluded_user_ids = [row[0] for row in session.execute(excluded_user_ids_query).fetchall()]
        else:
            excluded_user_ids = []

        # Calculate final user IDs to include (only users with roles)
        final_user_ids = [uid for uid in included_user_ids if uid not in excluded_user_ids]

        if not final_user_ids:
            return api_response(404, "No users found")

        # Create base statement with user ID filter using IN clause
        base_statement = sm_select(User).where(User.id.in_(final_user_ids))

    result = listop(
        session=session,
        Model=User,
        searchFields=searchFields,
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
        Statement=base_statement,
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