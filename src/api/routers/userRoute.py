from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Request,
)
from sqlalchemy import select,and_, update as sql_update
from src.api.core.email_service import send_verification_email,send_password_reset_confirmation
from src.api.core.operation import listop
import datetime
from src.api.core.security import hash_password
from src.api.core import updateOp, requireSignin
from src.api.core.dependencies import GetSession, requirePermission, requireAdmin
from src.api.core.response import api_response, raiseExceptions
from src.api.models.usersModel import UserCreate,RegisterUser, UpdateUserByAdmin, User, UserRead, UserUpdate,ChangePasswordRequest,ForgotPasswordRequest,VerifyCodeRequest,ResetPasswordRequest
from src.api.models.role_model.roleModel import Role
from src.api.models.role_model.userRoleModel import UserRole
import random

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
# @router.get("/list", response_model=list[UserRead])  # no response_model
# def list_users(
#     user: requireAdmin,
#     session: GetSession,
#     dateRange: Optional[
#         str
#     ] = None,  # JSON string like '["created_at", "01-01-2025", "01-12-2025"]'
#     numberRange: Optional[str] = None,  # JSON string like '["amount", "0", "100000"]'
#     searchTerm: str = None,
#     columnFilters: Optional[str] = Query(
#         None
#     ),  # e.g. '[["name","car"],["description","product"]]'
#     page: int = None,
#     skip: int = 0,
#     limit: int = Query(10, ge=1, le=200),
# ):

#     filters = {
#         "searchTerm": searchTerm,
#         "columnFilters": columnFilters,
#         "dateRange": dateRange,
#         "numberRange": numberRange,
#         # "customFilters": customFilters,
#     }

#     searchFields = [
#         "name",
#         "email",
#         "roles.name",
#         "roles.slug"
#     ]
#     result = listop(
#         session=session,
#         Model=User,
#         searchFields=searchFields,
#         filters=filters,
#         skip=skip,
#         page=page,
#         limit=limit,
#     )
#     if not result["data"]:
#         return api_response(404, "No User found")
#     data = [UserRead.model_validate(prod) for prod in result["data"]]

#     return api_response(
#         200,
#         "User found",
#         data,
#         result["total"],
#     )

# ✅ READ ALL with Role Search and Filter
@router.get("/list", response_model=list[UserRead])
def list_users(
    user: requireAdmin,
    session: GetSession,
    dateRange: Optional[str] = None,
    numberRange: Optional[str] = None,
    searchTerm: str = None,
    columnFilters: Optional[str] = Query(None),
    role: Optional[int] = Query(None, description="Filter by role ID"),  # Correct parameter name
    page: int = None,
    skip: int = 0,
    limit: int = Query(10, ge=1, le=200),
):
    filters = {
        "searchTerm": searchTerm,
        "columnFilters": columnFilters,
        "dateRange": dateRange,
        "numberRange": numberRange,
    }

    # Correct path through the relationship chain
    searchFields = [
        "name",
        "email",
        "user_roles.role.name",      # Correct path: User -> UserRole -> Role -> name
        "user_roles.role.slug"       # Correct path: User -> UserRole -> Role -> slug
    ]
    
    # Add custom filter for role_id in the format expected by listop
    if role is not None:
        # Format as list of tuples: [(column_path, value)]
        filters["customFilters"] = [("user_roles.role_id", role)]

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

@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    session: GetSession,
    user: requireSignin,
):
    """
    Change password for authenticated user
    """
    user_id = user.get("id")
    
    # Get the user object properly
    db_user = session.get(User, user_id)
    raiseExceptions((db_user, 404, "User not found"))
    
    # Verify current password
    from src.api.core.security import verify_password
    if not verify_password(request.current_password, db_user.password):
        return api_response(400, "Current password is incorrect")
    
    # Hash new password
    hashed_password = hash_password(request.new_password)
    db_user.password = hashed_password
    
    session.add(db_user)
    session.commit()
    
    return api_response(200, "Password changed successfully")

@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    session: GetSession,
):
    """
    Send verification code to user's email for password reset
    """
    # Find user by email using session.get() with a query result
    statement = select(User).where(User.email == request.email)
    db_user = session.exec(statement).first()
    
    # Don't reveal if user exists or not for security
    if not db_user:
        return api_response(200, "If the email exists, a verification code has been sent")
    
    # Generate 5-digit verification code
    verification_code = str(random.randint(10000, 99999))
    
    # Set expiration time (15 minutes from now)
    expires_at = datetime.datetime.now() + datetime.timedelta(minutes=15)
    print(f"verification_code:{verification_code}")
    print(f"expires_at:{expires_at}")
    
    # Use SQL update statement to update the user
    update_stmt = (
        sql_update(User)
        .where(User.email == request.email)
        .values(
            password_reset_code=verification_code,
            password_reset_code_expires=expires_at
        )
    )
    session.exec(update_stmt)
    session.commit()
    
    # TODO: Implement email service to send verification code
    # For now, we'll return the code in response (remove this in production)
    # Send email with verification code
    try:
        send_verification_email(request.email, verification_code)
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        # Continue even if email fails - user might retry
    print(f"Verification code for {request.email}: {verification_code}")
    
    return api_response(200, "Verification code sent to your email")

@router.post("/verify-code")
def verify_code(
    request: VerifyCodeRequest,
    session: GetSession,
):
    """
    Verify the password reset code
    """
    db_user = session.exec(
        select(User).where(
            and_(
                User.email == request.email,
                User.password_reset_code == request.verification_code,
                User.password_reset_code_expires > datetime.datetime.now()
            )
        )
    ).first()
    
    if not db_user:
        return api_response(400, "Invalid or expired verification code")
    
    return api_response(200, "Verification code is valid")

@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    session: GetSession,
):
    """
    Reset password using verification code
    """
    # First verify the code exists and is valid
    statement = select(User).where(
        and_(
            User.email == request.email,
            User.password_reset_code == request.verification_code,
            User.password_reset_code_expires > datetime.datetime.now()
        )
    )
    db_user = session.exec(statement).first()
    
    if not db_user:
        return api_response(400, "Invalid or expired verification code")
    
    # Hash new password
    hashed_password = hash_password(request.new_password)
    
    # Use SQL update statement to update the password and clear reset code
    update_stmt = (
        sql_update(User)
        .where(
            and_(
                User.email == request.email,
                User.password_reset_code == request.verification_code
            )
        )
        .values(
            password=hashed_password,
            password_reset_code=None,
            password_reset_code_expires=None
        )
    )
    session.exec(update_stmt)
    session.commit()
    try:
        send_password_reset_confirmation(request.email)
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

    return api_response(200, "Password reset successfully")