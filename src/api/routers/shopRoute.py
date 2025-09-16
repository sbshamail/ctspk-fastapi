from fastapi import APIRouter
from sqlmodel import select

from src.api.models.shop_model import (
    Shop,
    ShopCreate,
    ShopRead,
    ShopUpdate,
    ShopVerifyByAdmin,
)
from src.api.models.usersModel import User
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
from src.api.core.decorator import handle_async_wrapper

router = APIRouter(prefix="/shop", tags=["Shop"])


# ✅ CREATE shop
@router.post("/create")
@handle_async_wrapper
def create_shop(
    user: requireSignin,  # the logged-in user
    request: ShopCreate,
    session: GetSession,
):
    print(user)
    # 1️⃣ Create the shop
    new_shop = Shop(**request.model_dump(), owner_id=user.get("id"))
    session.add(new_shop)
    session.commit()
    session.refresh(new_shop)

    # 2️⃣ find the shop_admin role
    role = session.exec(select(Role).where(Role.name == "shop_admin")).first()

    raiseExceptions((role, 404, "Role not found"))

    # 3️⃣ Assign the shop_admin role to the user (if not already assigned)
    existing = session.exec(
        select(UserRole).filter(
            UserRole.user_id == user.get("id"), UserRole.role_id == role.id
        )
    ).first()
    if not existing:
        mapping = UserRole(user_id=user.get("id"), role_id=role.id)
        session.add(mapping)
        session.commit()

    read = ShopRead.model_validate(new_shop)
    return api_response(200, "Shop Created Successfully", read)


# ✅ READ single shop
@router.get("/read/{id}", response_model=ShopRead)
@handle_async_wrapper
def get_shop(id: int, session: GetSession, user: User):
    shop = session.get(Shop, id)
    raiseExceptions((shop, 404, "Shop not found"))
    return api_response(200, "Shop Found", ShopRead.model_validate(shop))


# ✅ UPDATE shop
@router.put("/update/{id}")
@handle_async_wrapper
def update_shop(id: int, request: ShopUpdate, session: GetSession, user: User):
    shop = session.get(Shop, id)
    raiseExceptions((shop, 404, "Shop not found"))

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(shop, key, value)

    session.add(shop)
    session.commit()
    session.refresh(shop)
    return api_response(200, "Shop Updated Successfully", ShopRead.model_validate(shop))


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
    verify = updateOp(db_shop, request, session)

    session.commit()
    session.refresh(db_shop)
    return api_response(200, "User Found", ShopRead.model_validate(db_shop))


# ✅ DELETE shop
@router.delete("/delete/{id}")
def delete_shop(id: int, session: GetSession, user: User):
    shop = session.get(Shop, id)
    raiseExceptions((shop, 404, "Shop not found"))

    session.delete(shop)
    session.commit()
    return api_response(200, "Shop Deleted Successfully")


# ✅ LIST shops (reusable listRecords)
@router.get("/list", response_model=list[ShopRead])
def list_shops(
    session: GetSession, query_params: ListQueryParams, user=requirePermission("all")
):
    query_params = vars(query_params)
    searchFields = ["name", "slug", "description"]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Shop,
        Schema=ShopRead,
    )
