from fastapi import APIRouter
from sqlalchemy import select

# core
from src.api.core.utility import Print
from src.api.core.middleware import handle_async_wrapper
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import GetSession, requirePermission
from src.api.core import api_response, raiseExceptions

# model
from src.api.models.role_model import Role, UserRole, UserRoleCreate
from src.api.models.role_model.schemas import UserRoleRead

router = APIRouter(prefix="/user-role", tags=["User Role Assign"])


# ✅ CREATE user-role
@router.post("/create")
@handle_async_wrapper
def create_user_role(
    request: UserRoleCreate,
    session: GetSession,
    user=requirePermission("role"),
):

    role = session.get(Role, request.role_id)
    raiseExceptions((role, 404, "Role not found"))
    # Check if the mapping already exists
    existing = session.exec(
        select(UserRole).filter(
            UserRole.user_id == request.user_id, UserRole.role_id == request.role_id
        )
    ).first()

    raiseExceptions((existing, 400, "UserRole mapping already exists", True))

    create = UserRole(**request.model_dump())

    session.add(create)
    session.commit()
    session.refresh(create)
    return api_response(200, "UserRole Created Successfully", create)


# ✅ READ a single user-role
@router.get("/read/{id}", response_model=UserRoleRead)
@handle_async_wrapper
def get_user_role(
    id: int,
    session: GetSession,
    user=requirePermission("role"),
):
    user_role = session.get(UserRole, id)
    raiseExceptions((user_role, 404, "UserRole not found"))
    read = UserRoleRead.model_validate(user_role)
    Print(user_role, "read")
    return api_response(200, "User  Role Found", read)


# ✅ DELETE a user-role
@router.delete("/delete/{id}")
def delete_user_role(
    id: int,
    session: GetSession,
    user=requirePermission("role-delete"),
):
    user_role = session.get(UserRole, id)
    raiseExceptions((user_role, 404, "UserRole not found"))

    session.delete(user_role)
    session.commit()
    return api_response(200, "UserRole Deleted Successfully")


# ✅ LIST user-roles
@router.get("/list", response_model=list[UserRoleRead])
def list_user_roles(
    session: GetSession,
    user=requirePermission("role"),
):
    query_params = vars(query_params)
    searchFields = [
        "title",
    ]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=UserRole,
        Schema=UserRoleRead,
    )
