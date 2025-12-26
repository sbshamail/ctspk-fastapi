from fastapi import APIRouter, Query
from sqlalchemy import select
from typing import Optional
from src.api.core.operation import listop
from src.api.core.response import api_response, raiseExceptions
from src.api.core.dependencies import GetSession, requirePermission
from src.api.models.role_model.roleModel import Role, RoleCreate, RoleRead, RoleUpdate
from src.api.models.role_model.userRoleModel import UserRole
from src.api.core.utility import uniqueSlugify

router = APIRouter(prefix="/role", tags=["Role"])

ROOT_PERMISSIONS = {"system:*", "all"}

@router.post("/create")
def create_role(
    request: RoleCreate,
    session: GetSession,
    user=requirePermission(["role:create"]),
):
    # Check if role name already exists
    existing_role = session.exec(
        select(Role).where(Role.name == request.name)
    ).first()
    if existing_role:
        return api_response(400, "Role name already exists")

    # Check for root permissions
    if any(p in ROOT_PERMISSIONS for p in request.permissions) and not user.is_root:
        return api_response(403, "You cannot assign root-level permissions")

    # Generate slug
    slug = uniqueSlugify(session, Role,request.name)
    
    # Check if slug already exists
    existing_slug = session.exec(
        select(Role).where(Role.slug == slug)
    ).first()
    if existing_slug:
        return api_response(400, "Slug already exists")

    role_data = request.model_dump()
    role_data["slug"] = slug
    print(f"role_data: {user}")
    role_data["user_id"] = user["id"]  # Current user creating the role

    role = Role(**role_data)
    session.add(role)
    session.commit()
    session.refresh(role)
    return api_response(201, "Role Created Successfully", RoleRead.model_validate(role))


@router.put("/update/{id}")
def update_role(
    id: int,
    request: RoleUpdate,
    session: GetSession,
    user=requirePermission(["role:update"]),
):
    role = session.get(Role, id)
    raiseExceptions((role, 404, "Role not found"))

    update_data = request.model_dump(exclude_unset=True)
    
    # Check for root permissions if permissions are being updated
    if "permissions" in update_data:
        if any(p in ROOT_PERMISSIONS for p in update_data["permissions"]) and not user.is_root:
            return api_response(403, "You cannot assign root-level permissions")
    
    # Check name uniqueness if name is being updated
    if "name" in update_data and update_data["name"] != role.name:
        existing_role = session.exec(
            select(Role).where(Role.name == update_data["name"])
        ).first()
        if existing_role:
            return api_response(400, "Role name already exists")

    # Check slug uniqueness if slug is being updated
    if "slug" in update_data and update_data["slug"] != role.slug:
        existing_slug = session.exec(
            select(Role).where(Role.slug == update_data["slug"])
        ).first()
        if existing_slug:
            return api_response(400, "Slug already exists")

    # Generate slug if name is updated but slug is not provided
    if "name" in update_data and "slug" not in update_data:
        update_data["slug"] = uniqueSlugify(update_data["name"])

    for field, value in update_data.items():
        if value is not None:
            setattr(role, field, value)

    session.add(role)
    session.commit()
    session.refresh(role)
    return api_response(200, "Role Updated Successfully", RoleRead.model_validate(role))


@router.get("/read/{id}")
def get_role(id: int, session: GetSession, user=requirePermission(["role:delete"])):
    role = session.get(Role, id)
    raiseExceptions((role, 404, "Role not found"))
    return api_response(200, "Role Found", RoleRead.model_validate(role))


@router.delete("/delete/{id}")
def delete_role(
    id: int,
    session: GetSession,
    user=requirePermission("role-delete"),
):
    role = session.get(Role, id)
    raiseExceptions((role, 404, "Role not found"))

    # Check if role is assigned to any users
    user_roles = session.exec(
        select(UserRole).where(UserRole.role_id == id)
    ).all()
    
    if user_roles:
        return api_response(400, "Cannot delete role assigned to users")

    session.delete(role)
    session.commit()
    return api_response(200, f"Role {role.name} deleted successfully")


@router.patch("/{id}/status")
def update_role_status(
    id: int,
    is_active: bool,
    session: GetSession,
    user=requirePermission(["role:update"]),
):
    role = session.get(Role, id)
    raiseExceptions((role, 404, "Role not found"))

    role.is_active = is_active
    session.add(role)
    session.commit()

    action = "activated" if is_active else "deactivated"
    return api_response(200, f"Role {action} successfully")


@router.get("/list", response_model=list[RoleRead])
def list_roles(
    session: GetSession,
    searchTerm: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = None,
    skip: int = 0,
    limit: int = Query(200, ge=1, le=200),
    user=requirePermission("role"),
):
    filters = {
        "searchTerm": searchTerm,
        "columnFilters": []
    }

    if is_active is not None:
        filters["columnFilters"].append(["is_active", str(is_active)])

    searchFields = ["name", "slug", "description"]

    result = listop(
        session=session,
        Model=Role,
        searchFields=searchFields,
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
    )

    if not result["data"]:
        return api_response(404, "No roles found")

    roles_data = [RoleRead.model_validate(role) for role in result["data"]]
    return api_response(200, "Roles found", roles_data, result["total"])