from fastapi import APIRouter
from sqlalchemy import select
from src.api.core.utility import slugify, uniqueSlugify
from src.api.core.middleware.decorator import handle_async_wrapper
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.manufacturer_model import (
    Manufacturer,
    ManufacturerCreate,
    ManufacturerRead,
    ManufacturerUpdate,
    ManufacturerApproved,
    ManufacturerActivate
)
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)


router = APIRouter(prefix="/manufacturer", tags=["Manufacturer"])


@router.post("/create")
def create_role(
    request: ManufacturerCreate,
    session: GetSession,
    user=requirePermission("manufacturer"),
):
    manufacturer = Manufacturer(**request.model_dump())
    manufacturer.slug = uniqueSlugify(
        session,
        Manufacturer,
        manufacturer.name,
    )
    session.add(manufacturer)
    session.commit()
    session.refresh(manufacturer)
    return api_response(200, "Manufacturer Created Successfully", manufacturer)


@router.put("/update/{id}", response_model=ManufacturerRead)
def update_role(
    id: int,
    request: ManufacturerUpdate,
    session: GetSession,
    user=requirePermission("manufacturer"),
):
    manufacturer = session.get(Manufacturer, id)  # Like findById
    raiseExceptions((manufacturer, 404, "Manufacturer not found"))
    data = updateOp(manufacturer, request, session)

    if data.name:
        data.slug = uniqueSlugify(session, Manufacturer, data.name)
    session.commit()
    session.refresh(data)
    return api_response(200, "Manufacturer Update Successfully", data)


@router.get("/read/{id_slug}", description="Manufacturer ID (int) or slug (str)")
def get_role(id_slug: str, session: GetSession):
    manufacturer = None

    # Check if it's an integer ID
    if id_slug.isdigit():
        manufacturer = session.get(Manufacturer, int(id_slug))
    else:
        # Otherwise treat as slug
        manufacturer = (
            session.exec(select(Manufacturer).where(Manufacturer.slug.ilike(id_slug)))
            .scalars()
            .first()
        )

    raiseExceptions((manufacturer, 404, "Manufacturer not found"))
    return api_response(
        200, "Manufacturer Found", ManufacturerRead.model_validate(manufacturer)
    )


# ❗ DELETE
@router.delete("/delete/{id}", response_model=dict)
def delete_role(
    id: int,
    session: GetSession,
    user=requirePermission("manufacturer"),
):
    manufacturer = session.get(Manufacturer, id)
    raiseExceptions((manufacturer, 404, "Manufacturer not found"))

    session.delete(manufacturer)
    session.commit()
    return api_response(404, f"Manufacturer {manufacturer.id} deleted")


# ✅ LIST
@router.get("/list", response_model=list[ManufacturerRead])
def list(query_params: ListQueryParams):
    query_params = vars(query_params)
    searchFields = []
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Manufacturer,
        Schema=ManufacturerRead,
    )

# ✅ PATCH Manufacturer status (toggle/verify)
@router.patch("/{id}/status")
def patch_manufacturer_status(
    id: int,
    request: ManufacturerActivate,
    session: GetSession,
    user=requirePermission(["system:*"]),  # 🔒 both allowed
):
    manufacturer = session.get(Manufacturer, id)
    raiseExceptions((manufacturer, 404, "Manufacturer not found"))

    # only update status fields
    updated = updateOp(manufacturer, request, session)

    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Manufacturer status updated successfully", ManufacturerRead.model_validate(updated))

# ✅ PATCH Manufacturer Approved (toggle/verify)
@router.patch("/{id}/approval")
def patch_manufacturer_approved(
    id: int,
    request: ManufacturerApproved,
    session: GetSession,
    user=requirePermission(["system:*"]),  # 🔒 both allowed
):
    manufacturer = session.get(Manufacturer, id)
    raiseExceptions((manufacturer, 404, "Manufacturer not found"))

    # only update status fields
    updated = updateOp(manufacturer, request, session)

    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Manufacturer Approved/Disapproved updated successfully", ManufacturerRead.model_validate(updated))