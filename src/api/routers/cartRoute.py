from fastapi import APIRouter
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.cart_model import Cart, CartCreate, CartRead, CartUpdate
from src.api.core.dependencies import GetSession, ListQueryParams, requireSignin


router = APIRouter(prefix="/cart", tags=["Cart"])


@router.post("/create")
def create_role(
    request: CartCreate,
    session: GetSession,
    user: requireSignin,
):

    cart = Cart(**request.model_dump())
    cart.user_id = user.get("id")
    session.add(cart)
    session.commit()
    session.refresh(cart)
    return api_response(200, "Cart Created Successfully", cart)


@router.put("/update/{id}", response_model=CartRead)
def update_role(
    id: int,
    request: CartUpdate,
    session: GetSession,
    user: requireSignin,
):
    cart = session.get(Cart, id)  # Like findById
    raiseExceptions((cart, 404, "Cart not found"))
    updateOp(cart, request, session)

    # Ensure min quantity = 1
    if request.quantity is not None and request.quantity < 1:
        request.quantity = 1
    session.commit()
    session.refresh(cart)
    return api_response(200, "Cart Update Successfully", cart)


@router.get("/read/{id}")
def get_role(id: int, session: GetSession, user: requireSignin):

    cart = session.get(Cart, id)  # Like findById
    raiseExceptions((cart, 404, "Cart not found"))

    return api_response(200, "Cart Found", cart)


# ❗ DELETE
@router.delete("/delete/{id}", response_model=dict)
def delete_role(
    id: int,
    session: GetSession,
    user: requireSignin,
):
    cart = session.get(Cart, id)
    raiseExceptions((cart, 404, "Cart not found"))

    session.delete(cart)
    session.commit()
    return api_response(404, f"Cart {cart.id} deleted")


# ✅ LIST
@router.get("/list", response_model=list[CartRead])
def list(query_params: ListQueryParams, user: requireSignin):
    query_params = vars(query_params)
    searchFields = []
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Cart,
        Schema=CartRead,
    )
