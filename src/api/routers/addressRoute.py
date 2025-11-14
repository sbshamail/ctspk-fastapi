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
    Location,
)

router = APIRouter(prefix="/address", tags=["Address"])


# ✅ CREATE
@router.post("/create")
def create_address(
    request: AddressCreate,
    session: GetSession,
    user: requireSignin,
):
    print("📦 Incoming request:", request.model_dump())
    
    # Handle missing location by setting default values
    request_data = request.model_dump()
    request_data['customer_id'] = user.get("id")
    if request_data.get('location') is None:
        request_data['location'] = {"lat": 0.0, "lng": 0.0}
    
    address = Address(**request_data)
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
    user: requireSignin,
):
    address = session.get(Address, id)
    raiseExceptions((address, 404, "Address not found"))
    
    # ✅ OWNERSHIP CHECK - User can only update their own addresses
    if address.customer_id != user.get("id"):
        raiseExceptions((None, 403, "You can only update your own addresses"))

    # Handle location update - only update if provided
    update_data = request.model_dump(exclude_unset=True)
    # Don't allow changing customer_id through update
    if 'customer_id' in update_data:
        del update_data['customer_id']
    
    # If location is being set to None, handle it properly
    if 'location' in update_data and update_data['location'] is None:
        update_data['location'] = {"lat": 0.0, "lng": 0.0}
    
    # Manually update the address fields instead of using updateOp
    for field, value in update_data.items():
        if hasattr(address, field):
            setattr(address, field, value)
    
    session.commit()
    session.refresh(address)

    return api_response(200, "Address Updated Successfully", AddressRead.model_validate(address))


# ✅ READ (ID)
@router.get("/read/{id}")
def get_address(id: int, session: GetSession, user: requireSignin):
    address = session.get(Address, id)
    raiseExceptions((address, 404, "Address not found"))
    
    # ✅ OWNERSHIP CHECK - User can only read their own addresses
    if address.customer_id != user.get("id"):
        raiseExceptions((None, 403, "You can only view your own addresses"))

    return api_response(200, "Address Found", AddressRead.model_validate(address))


# ✅ DELETE
@router.delete("/delete/{id}")
def delete_address(
    id: int,
    session: GetSession,
    user: requireSignin,
):
    address = session.get(Address, id)
    raiseExceptions((address, 404, "Address not found"))
    
    # ✅ OWNERSHIP CHECK - User can only delete their own addresses
    if address.customer_id != user.get("id"):
        raiseExceptions((None, 403, "You can only delete your own addresses"))

    session.delete(address)
    session.commit()
    return api_response(200, f"Address {address.id} deleted successfully")


# ✅ LIST (paginated, searchable) - Only user's addresses
@router.get("/list", response_model=list[AddressRead])
def list_addresses(query_params: ListQueryParams, user: requireSignin):
    query_params = vars(query_params)
    searchFields = ["title", "type"]  # fields to search on
    
    # ✅ Add customer_id filter to only show user's addresses
    if not hasattr(query_params, 'filters'):
        query_params['filters'] = {}
    query_params['filters']['customer_id'] = user.get("id")
    
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Address,
        Schema=AddressRead,
    )