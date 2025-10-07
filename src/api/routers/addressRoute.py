from fastapi import APIRouter
from sqlalchemy import select
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)
from src.api.models.addressModel import (
    Address,
    AddressCreate,
    AddressUpdate,
    AddressRead,
)

router = APIRouter(prefix="/address", tags=["Address"])


# ✅ CREATE
@router.post("/create")
def create_address(
    request: AddressCreate,
    session: GetSession,
    user=requirePermission("system:*"),
):
    print("📦 Incoming request:", request.model_dump())

    address = Address(**request.model_dump())
    session.add(address)
    session.commit()
    session.refresh(address)
    return api_response(
        200, "Address Created Successfully", AddressRead.model_validate(address)
    )


# ✅ UPDATE
@router.put("/update/{id}")
def update_address(
    id: int,
    request: AddressUpdate,
    session: GetSession,
    user=requirePermission("system:*"),
):
    address = session.get(Address, id)
    raiseExceptions((address, 404, "Address not found"))

    updated = updateOp(address, request, session)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Address Updated Successfully", AddressRead.model_validate(updated))


# ✅ READ (ID)
@router.get("/read/{id}")
def get_address(id: int, session: GetSession):
    address = session.get(Address, id)
    raiseExceptions((address, 404, "Address not found"))

    return api_response(200, "Address Found", AddressRead.model_validate(address))


# ✅ DELETE
@router.delete("/delete/{id}")
def delete_address(
    id: int,
    session: GetSession,
    user=requirePermission("system:*"),
):
    address = session.get(Address, id)
    raiseExceptions((address, 404, "Address not found"))

    session.delete(address)
    session.commit()
    return api_response(200, f"Address {address.id} deleted successfully")


# ✅ LIST (paginated, searchable)
@router.get("/list", response_model=list[AddressRead])
def list_addresses(query_params: ListQueryParams, user=requireSignin):
    query_params = vars(query_params)
    searchFields = ["title", "type"]  # fields to search on
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Address,
        Schema=AddressRead,
    )
