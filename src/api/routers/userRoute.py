from typing import Optional, List
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Request,
)
from sqlalchemy import select,and_, update as sql_update
from src.api.core.email_service import send_verification_email,send_password_reset_confirmation
from src.api.core.operation import listop
from src.api.core.avatar_helper import get_user_avatar
import datetime
from src.api.core.security import hash_password
from src.api.core import updateOp, requireSignin
from src.api.core.dependencies import GetSession, requirePermission, requireAdmin
from src.api.core.response import api_response, raiseExceptions
from src.api.models.usersModel import UserCreate,RegisterUser, UpdateUserByAdmin, User, UserRead, UserUpdate,ChangePasswordRequest,ForgotPasswordRequest,VerifyCodeRequest,ResetPasswordRequest,ProfileUpdate
from src.api.models.role_model.roleModel import Role
from src.api.models.role_model.userRoleModel import UserRole
from src.api.models.shop_model.shopsModel import Shop
from src.api.models.shop_model.userShopModel import UserShop
import random

router = APIRouter(prefix="/user", tags=["user"])


def serialize_user_with_avatar(user: User) -> UserRead:
    """
    Serialize user and add avatar field
    """
    user_read = UserRead.model_validate(user)
    # Add avatar field using helper function
    user_read.avatar = get_user_avatar(user.image, user.name)
    return user_read

@router.post("/create")
def create_user(
    request: UserCreate,
    session: GetSession,
    user=requirePermission("user:create"),
):
    # Check if user already exists
    existing_user = session.exec(
        select(User).where(User.email == request.email)
    ).first()
    if existing_user:
        return api_response(400, "User with this email already exists")

    # Hash password
    hashed_password = hash_password(request.password)

    # Create user data (exclude role_ids, shop_ids and confirm_password)
    user_data = request.model_dump(exclude={'password', 'confirm_password', 'role_ids', 'shop_ids'})
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

    # Assign shops if shop_ids are provided
    if request.shop_ids:
        for shop_id in request.shop_ids:
            # Check if shop exists
            shop = session.get(Shop, shop_id)
            if not shop:
                session.rollback()
                return api_response(404, f"Shop with ID {shop_id} not found")

            # Check if user-shop relationship already exists
            existing_user_shop = session.exec(
                select(UserShop).where(
                    UserShop.user_id == new_user.id,
                    UserShop.shop_id == shop_id
                )
            ).first()

            if not existing_user_shop:
                user_shop = UserShop(user_id=new_user.id, shop_id=shop_id)
                session.add(user_shop)

    session.commit()
    session.refresh(new_user)

    return api_response(201, "User created successfully", serialize_user_with_avatar(new_user))
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
    return api_response(200, "User Updated", serialize_user_with_avatar(db_user))

@router.put("/profile", response_model=UserRead)
def update_profile(
    user: requireSignin,
    request: ProfileUpdate,
    session: GetSession,
):
    user_id = user.get("id")
    db_user = session.get(User, user_id)
    raiseExceptions((db_user, 404, "User not found"))

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # Only update image if it's provided (not None) in the request
        if field == "image":
            if value is not None:
                setattr(db_user, field, value)
        else:
            setattr(db_user, field, value)

    session.commit()
    session.refresh(db_user)
    return api_response(200, "Profile updated successfully", serialize_user_with_avatar(db_user))

@router.put("/updatebyadmin/{user_id}", response_model=UserRead)
def update_user_by_admin(
    user_id: int,
    request: UpdateUserByAdmin,  # You might want to create a UserUpdateWithRoles schema
    session: GetSession,
    user=requirePermission("user:update"),
):
    db_user = session.get(User, user_id)
    raiseExceptions((db_user, 404, "User not found"))

    update_data = request.model_dump(exclude_unset=True, exclude={'role_ids', 'shop_ids'})

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

    # Handle shop assignments if shop_ids are provided
    if hasattr(request, 'shop_ids') and request.shop_ids is not None:
        # Remove existing user shops
        existing_user_shops = session.exec(
            select(UserShop).where(UserShop.user_id == user_id)
        ).all()
        for user_shop in existing_user_shops:
            session.delete(user_shop)

        # Add new user shops
        for shop_id in request.shop_ids:
            shop = session.get(Shop, shop_id)
            if shop:
                user_shop = UserShop(user_id=user_id, shop_id=shop_id)
                session.add(user_shop)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return api_response(200, "User updated successfully", serialize_user_with_avatar(db_user))

@router.get("/read", response_model=UserRead)
def get_user(
    user: requireSignin,
    session: GetSession,
):
    user_id = user.get("id")
    db_user = session.get(User, user_id)  # Like findById
    raiseExceptions((db_user, 400, "User not found"))

    try:
        # Query for active free shipping coupon
        from src.api.models.couponModel import Coupon, CouponType
        from datetime import datetime, timedelta, timezone
        from src.api.core.email_helper import send_email
        current_time = datetime.now(timezone.utc)
        free_shipping_coupon = session.execute(
            select(Coupon)
            .where(Coupon.type == CouponType.FREE_SHIPPING)
            .where(Coupon.active_from <= current_time)
            .where(Coupon.expire_at >= current_time)
            .where(Coupon.deleted_at == None)
        ).scalars().first()

        # Prepare email replacements
        replacements = {
            "name": db_user.name,
            "customer_name": db_user.name,
            "email": db_user.email,
        }

        # Add coupon details if available
        if free_shipping_coupon:
            replacements.update({
                "coupon_code": free_shipping_coupon.code,
                "coupon_valid_from": free_shipping_coupon.active_from.strftime("%B %d, %Y"),
                "coupon_valid_to": free_shipping_coupon.expire_at.strftime("%B %d, %Y"),
                "coupon_minimum_amount": f"{free_shipping_coupon.minimum_cart_amount:.2f}",
                "coupon_code_text":"Code:",
                "date":"Date:",
                "min_amount_text":"Minimum Cart Amount:"
            })
        else:
            # Provide empty values if no coupon available
            replacements.update({
                "coupon_code": "",
                "coupon_valid_from": "",
                "coupon_valid_to": "",
                "coupon_minimum_amount": "",
                "coupon_code_text":"",
                "date":"",
                "min_amount_text":""
            })

        send_email(
            to_email=db_user.email,
            email_template_id=3,  # Use appropriate template ID for user registration
            replacements=replacements,
        )
    except Exception as e:
        # Log email error but don't fail registration
        import traceback
        print(f"Failed to send registration email: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"Full traceback:\n{traceback.format_exc()}")

    return api_response(200, "User Found", serialize_user_with_avatar(db_user))


# ✅ DELETE
@router.delete("/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    session: GetSession,
    user=requirePermission("user:delete"),
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
    session: GetSession,
    user=requirePermission("user:view"),
    dateRange: Optional[str] = None,
    numberRange: Optional[str] = None,
    searchTerm: str = None,
    columnFilters: Optional[str] = Query(None),
    role: Optional[int] = Query(None, description="Filter by single role ID (legacy)"),
    role_ids: Optional[List[int]] = Query(None, description="Filter by allowed role IDs (include users with these roles)"),
    exclude_role_ids: Optional[List[int]] = Query(None, description="Filter by excluded role IDs (exclude users with these roles)"),
    customer: Optional[bool] = Query(None, description="If true, show only users without any roles (customers)"),
    page: int = None,
    skip: int = 0,
    limit: int = Query(10, ge=1, le=200),
):
    """
    List users with role filtering options:
    - role: Filter by single role ID (legacy support)
    - role_ids: Include users with ANY of these role IDs (allowed roles)
    - exclude_role_ids: Exclude users with ANY of these role IDs (not allowed roles)
    - customer: If true, show only users without any roles (customers)

    Examples:
    - /user/list?role_ids=1&role_ids=2 - Get users with role 1 OR role 2
    - /user/list?exclude_role_ids=3&exclude_role_ids=4 - Get users WITHOUT role 3 AND role 4
    - /user/list?role_ids=1&role_ids=2&exclude_role_ids=3 - Get users with role 1 or 2, but NOT role 3
    - /user/list?customer=true - Get users without any roles (customers only)
    """
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

    # Build custom query for role filtering
    # If role_ids or exclude_role_ids are provided, we need custom SQL filtering
    from sqlalchemy import select as sa_select, distinct
    from sqlmodel import select as sm_select

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
    elif role_ids or exclude_role_ids or role:
        # Get user IDs that match the role criteria
        if role_ids or role:
            # Get users who have ANY of the allowed role_ids
            allowed_roles = role_ids if role_ids else ([role] if role else [])
            included_user_ids_query = (
                sa_select(distinct(UserRole.user_id))
                .where(UserRole.role_id.in_(allowed_roles))
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
            return api_response(404, "No User found")

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
        return api_response(404, "No User found")

    data = [serialize_user_with_avatar(prod) for prod in result["data"]]

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
    verification_code = str(random.randint(100000, 999999))
    
    # Set expiration time (15 minutes from now)
    expires_at = datetime.datetime.now() + datetime.timedelta(minutes=300)
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
    #,
    #            User.password_reset_code_expires > datetime.datetime.now()
    print(f"db_user:{db_user}")
    print(f"date:{datetime.datetime.now()}")
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