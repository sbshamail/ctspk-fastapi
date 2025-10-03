from fastapi import APIRouter
from sqlalchemy import select
from src.api.core.utility import slugify, uniqueSlugify
from src.api.core.middleware.decorator import handle_async_wrapper
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.shipping_model import (
    Shipping,
    ShippingCreate,
    ShippingRead,
    ShippingUpdate,
    ShippingActivate
)
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)


router = APIRouter(prefix="/shipping", tags=["Shipping"])


@router.post("/create")
def create_role(
    request: ShippingCreate,
    session: GetSession,
    user=requirePermission("system:*"),
):
    # Debug print
   # print("📦 Incoming request:", request.model_dump())

    # Create ORM object
    shipping = Shipping(**request.model_dump())

    # Auto-generate slug
    shipping.slug = uniqueSlugify(session, Shipping, shipping.name)

    # Save to DB
    session.add(shipping)
    session.commit()
    session.refresh(shipping)

    return api_response(200, "Shipping Created Successfully", ShippingRead.model_validate(shipping))

@router.put("/update/{id}", response_model=ShippingRead)
def update_role(
    id: int,
    request: ShippingUpdate,
    session: GetSession,
    user=requirePermission("system:*"),
):
    shipping = session.get(Shipping, id)  # Like findById
    raiseExceptions((shipping, 404, "Shipping not found"))

    data = updateOp(shipping, request, session)

    if data.name:
        data.slug = uniqueSlugify(session, Shipping, data.name)
    session.commit()
    session.refresh(data)
    return api_response(200, "Shipping Update Successfully", ShippingRead.model_validate(data))


@router.get("/read/{id_slug}", description="shipping ID (int) or slug (str)")
def get_role(id_slug: str, session: GetSession):
    shipping = None

    # Check if it's an integer ID
    if id_slug.isdigit():
        shipping = session.get(Shipping, int(id_slug))
    else:
        # Otherwise treat as slug
        shipping = (
            session.exec(select(Shipping).where(Shipping.slug.ilike(id_slug)))
            .scalars()
            .first()
        )

    raiseExceptions((shipping, 404, "shipping not found"))
    return api_response(
        200, "Shipping Found", ShippingRead.model_validate(shipping)
    )


# ❗ DELETE
@router.delete("/delete/{id}", response_model=dict)
def delete_role(
    id: int,
    session: GetSession,
    user=requirePermission("system:*"),
):
    shipping = session.get(Shipping, id)
    raiseExceptions((shipping, 404, "shipping not found"))

    session.delete(shipping)
    session.commit()
    return api_response(404, f"Shipping {shipping.id} deleted")


# ✅ LIST
@router.get("/list", response_model=list[ShippingRead])
def list(query_params: ListQueryParams, user: requireSignin):
    query_params = vars(query_params)
    searchFields = []
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Shipping,
        Schema=ShippingRead,
    )

# ✅ PATCH shipping status (toggle/verify)
@router.patch("/{id}/status")
def patch_shipping_status(
    id: int,
    request: ShippingActivate,
    session: GetSession,
    user=requirePermission(["system:*"]),  # 🔒 both allowed
):
    shipping = session.get(Shipping, id)
    raiseExceptions((shipping, 404, "shipping not found"))

    # only update status fields
    updated = updateOp(shipping, request, session)

    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Shipping status updated successfully", ShippingRead.model_validate(updated))
