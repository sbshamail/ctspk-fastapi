from typing import Optional
from fastapi import APIRouter, Query
from sqlmodel import select

from src.api.core.utility import uniqueSlugify
from src.api.models.shop_model import (
    Shop,
    ShopCreate,
    ShopRead,
    ShopUpdate,
    ShopVerifyByAdmin,
)

from src.api.models.role_model.userRoleModel import UserRole
from src.api.models.role_model.roleModel import Role
from src.api.core import (
    GetSession,
    ListQueryParams,
    listRecords,
    requireSignin,
    requirePermission,
    updateOp,
)
from src.api.core.response import api_response, raiseExceptions
from src.api.core.middleware import handle_async_wrapper
from src.api.core.notification_helper import NotificationHelper

router = APIRouter(prefix="/shop", tags=["Shop"])


# ✅ CREATE shop
@router.post("/create")
def create_shop(
    user: requireSignin,  # the logged-in user
    request: ShopCreate,
    session: GetSession,
):
    with session.begin():  # 🔑 single transaction

        # 1️⃣ Create the shop
        data = Shop(**request.model_dump(), owner_id=user.get("id"))
        data.slug = uniqueSlugify(session, Shop, data.name)
        session.add(data)

        # 2️⃣ find the shop_admin role
        role = session.exec(select(Role).where(Role.name == "shop_admin")).first()
        raiseExceptions((role, 404, "Role not found"))

        # 3️⃣ Assign the shop_admin role to the user (if not already assigned)
        existing = session.exec(
            select(UserRole).where(
                UserRole.user_id == user.get("id"),
                UserRole.role_id == role.id,
            )
        ).first()

        if not existing:
            mapping = UserRole(user_id=user.get("id"), role_id=role.id)
            session.add(mapping)

    # 🔒 commit happens automatically on context exit, rollback on error
    session.refresh(data)

    # Send notifications
    NotificationHelper.notify_shop_created(
        session=session,
        shop_id=data.id,
        shop_name=data.name
    )

    read = ShopRead.model_validate(data)
    return api_response(200, "Shop Created Successfully", read)


@router.get(
    "/read/{id_slug}",
    description="Shop ID (int) or slug (str)",
    response_model=ShopRead,
)
def get(id_slug: str, session: GetSession):
    # Check if it's an integer ID
    if id_slug.isdigit():
        read = session.get(Shop, int(id_slug))
    else:
        # Otherwise treat as slug
        read = session.exec(select(Shop).where(Shop.slug.ilike(id_slug))).first()
    raiseExceptions((read, 404, "Shop not found"))

    return api_response(200, "Shop Found", ShopRead.model_validate(read))


# ✅ UPDATE shop
@router.put("/update/{id}")
@handle_async_wrapper
def update_shop(
    id: int,
    request: ShopUpdate,
    session: GetSession,
    user=requirePermission("shop_admin"),
):
    shop = session.get(Shop, id)
    raiseExceptions((shop, 404, "Shop not found"))
    if user.get("id") != shop.owner_id:
        return api_response(403, "You are not the owner of this shop")
    data = updateOp(shop, request, session)
    if data.name:
        data.slug = uniqueSlugify(session, Shop, data.name)

    session.add(data)
    session.commit()
    session.refresh(data)
    return api_response(200, "Shop Updated Successfully", ShopRead.model_validate(data))


# ✅ UPDATE shop Status
@router.put("/shop_status_update/{shop_id}")
def update_shop(
    shop_id: int,
    request: ShopVerifyByAdmin,
    session: GetSession,
    user=requirePermission("system:*"),
):
    db_shop = session.get(Shop, shop_id)  # Like findById
    raiseExceptions((db_shop, 404, "Shop not found"))

    # Track previous status for notification
    was_active = db_shop.is_active

    verify = updateOp(db_shop, request, session)

    session.commit()
    session.refresh(db_shop)

    # Send notifications based on status change
    if db_shop.is_active and not was_active:
        # Shop was approved
        NotificationHelper.notify_shop_approved(
            session=session,
            shop_id=db_shop.id
        )
    elif not db_shop.is_active and was_active:
        # Shop was disapproved
        NotificationHelper.notify_shop_disapproved(
            session=session,
            shop_id=db_shop.id,
            reason="Shop status changed by admin"
        )

    return api_response(200, "Shop Status Updated", ShopRead.model_validate(db_shop))


# ✅ DELETE shop
@router.delete("/delete/{id}")
def delete_shop(id: int, session: GetSession, user=requirePermission("shop_admin")):
    shop = session.get(Shop, id)
    raiseExceptions((shop, 404, "Shop not found"))

    session.delete(shop)
    session.commit()
    return api_response(200, "Shop Deleted Successfully")


# ✅ LIST shops (reusable listRecords)
@router.get("/list", response_model=list[ShopRead])
def list_shops(
    session: GetSession,
    query_params: ListQueryParams,
    user=requirePermission("all"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    query_params = vars(query_params)

    # Add is_active to customFilters if provided
    if is_active is not None:
        query_params["customFilters"] = [["is_active", is_active]]

    searchFields = ["name", "slug", "description"]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Shop,
        Schema=ShopRead,
    )
# ✅ LIST shops for signed-in user
@router.get("/my-shops", response_model=list[ShopRead])
def my_shops(
    session: GetSession,
    query_params: ListQueryParams,
    user: requireSignin,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    query_params = vars(query_params)
    searchFields = ["name", "slug", "description"]

    # Filter shops by owner_id matching signed-in user
    # columnFilters expects string format: [["column", "value"]]
    user_id = user.get("id")
    query_params["columnFilters"] = f'[["owner_id", {user_id}]]'

    # Add is_active to customFilters if provided
    if is_active is not None:
        query_params["customFilters"] = [["is_active", is_active]]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Shop,
        Schema=ShopRead,
    )
# ✅ PATCH shop status (toggle/verify)
@router.patch("/{id}/status")
def patch_shop_status(
    id: int,
    request: ShopVerifyByAdmin,
    session: GetSession,
    user=requirePermission(["system:*", "shop_admin"]),  # 🔒 both allowed
):
    shop = session.get(Shop, id)
    raiseExceptions((shop, 404, "Shop not found"))

    # only update status fields
    updated = updateOp(shop, request, session)

    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Shop status updated successfully", ShopRead.model_validate(updated))