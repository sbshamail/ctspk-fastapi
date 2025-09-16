from fastapi import APIRouter
from sqlmodel import select

from src.api.core.utility import Print
from src.api.models.shop_model import Shop, UserShop, UserShopCreate, UserShopRead
from src.api.models.usersModel import User
from src.api.core.dependencies import GetSession, ListQueryParams, requirePermission
from src.api.core.operation import listRecords
from src.api.core.response import api_response, raiseExceptions
from src.api.core.decorator import handle_async_wrapper

router = APIRouter(prefix="/user-shop", tags=["UserShop"])


# ✅ CREATE UserShop
@router.post("/create")
@handle_async_wrapper
def create_user_shop(
    request: UserShopCreate,
    session: GetSession,
    user=requirePermission("shop_admin"),
):
    # 1️⃣ Ensure target user exists
    target_user = session.get(User, request.user_id)

    # 2️⃣ Ensure shop exists
    target_shop = session.get(Shop, request.shop_id)

    raiseExceptions(
        (not target_shop, 404, "Shop not found", True),
        (not target_user, 404, "User not found", True),
    )

    # 3️⃣ Only shop owner can assign users
    if target_shop.owner_id != user.get("id"):
        return api_response(403, "You are not the owner of this shop")

    if target_shop.is_active == False:
        return api_response(403, "You cannot assign users to inactive shop")

    # 4️⃣ Prevent duplicate assignment
    existing = session.exec(
        select(UserShop).filter(
            UserShop.user_id == request.user_id,
            UserShop.shop_id == request.shop_id,
        )
    ).first()
    raiseExceptions((existing, 400, "User already assigned to this shop", True))

    # 5️⃣ Create mapping
    create = UserShop(**request.model_dump())
    session.add(create)
    session.commit()
    session.refresh(create)

    return api_response(
        200,
        "User assigned to shop successfully",
        UserShopRead.model_validate(create),
    )


# ✅ READ single UserShop
@router.get("/read/{id}", response_model=UserShopRead)
@handle_async_wrapper
def get_user_shop(id: int, session: GetSession, user=requirePermission("shop_admin")):
    user_shop = session.get(UserShop, id)
    raiseExceptions((user_shop, 404, "UserShop not found"))
    read = UserShopRead.model_validate(user_shop)
    return api_response(200, "UserShop found", read)


# ✅ DELETE UserShop
@router.delete("/delete/{id}")
def delete_user_shop(
    id: int, session: GetSession, user=requirePermission("shop_admin")
):
    user_shop = session.get(UserShop, id)
    raiseExceptions((user_shop, 404, "UserShop not found"))

    session.delete(user_shop)
    session.commit()
    return api_response(200, "User removed from shop successfully")


# ✅ LIST UserShops
@router.get("/list", response_model=list[UserShopRead])
def list_user_shops(
    query_params: ListQueryParams,
    user=requirePermission("shop_admin"),
):
    query_params = vars(query_params)
    searchFields = []  # no text fields here, but you can filter by ids
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=UserShop,
        Schema=UserShopRead,
    )
