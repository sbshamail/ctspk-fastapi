# tax_route.py
from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select
from src.api.core.utility import slugify, uniqueSlugify
from src.api.core.middleware.decorator import handle_async_wrapper
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.taxModel import (
    Tax,
    TaxCreate,
    TaxRead,
    TaxUpdate,
    TaxActivate,
    TaxShippingToggle
)
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)


router = APIRouter(prefix="/tax", tags=["Tax"])


@router.post("/create")
def create_tax(
    request: TaxCreate,
    session: GetSession,
    user=requirePermission("tax:create"),
):
    # Create ORM object
    tax = Tax(**request.model_dump())

    # Save to DB
    session.add(tax)
    session.commit()
    session.refresh(tax)

    return api_response(200, "Tax Created Successfully", TaxRead.model_validate(tax))


@router.put("/update/{id}", response_model=TaxRead)
def update_tax(
    id: int,
    request: TaxUpdate,
    session: GetSession,
    user=requirePermission("tax:update"),
):
    tax = session.get(Tax, id)
    raiseExceptions((tax, 404, "Tax not found"))

    data = updateOp(tax, request, session)
    session.commit()
    session.refresh(data)
    return api_response(200, "Tax Updated Successfully", TaxRead.model_validate(data))


@router.get("/read/{id}", description="Get tax by ID")
def get_tax(id: int, session: GetSession):
    tax = session.get(Tax, id)
    raiseExceptions((tax, 404, "Tax not found"))
    return api_response(200, "Tax Found", TaxRead.model_validate(tax))


@router.delete("/delete/{id}", response_model=dict)
def delete_tax(
    id: int,
    session: GetSession,
    user=requirePermission("tax:delete"),
):
    tax = session.get(Tax, id)
    raiseExceptions((tax, 404, "Tax not found"))

    session.delete(tax)
    session.commit()
    return api_response(200, f"Tax {tax.id} deleted")


@router.get("/list", response_model=list[TaxRead])
def list_taxes(
    query_params: ListQueryParams,
    user: requireSignin,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    query_params = vars(query_params)

    # Add is_active to customFilters if provided
    if is_active is not None:
        query_params["customFilters"] = [["is_active", is_active]]

    searchFields = ["name", "country", "state", "city"]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Tax,
        Schema=TaxRead,
    )


@router.patch("/{id}/global")
def patch_tax_global(
    id: int,
    request: TaxActivate,
    session: GetSession,
    user=requirePermission(["tax:activate","tax:deactivate"]),
):
    tax = session.get(Tax, id)
    raiseExceptions((tax, 404, "Tax not found"))

    updated = updateOp(tax, request, session)
    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Tax global status updated successfully", TaxRead.model_validate(updated))


@router.patch("/{id}/shipping-toggle")
def patch_tax_shipping(
    id: int,
    request: TaxShippingToggle,
    session: GetSession,
    user=requirePermission(["tax:activate","tax:deactivate"]),
):
    tax = session.get(Tax, id)
    raiseExceptions((tax, 404, "Tax not found"))

    updated = updateOp(tax, request, session)
    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Tax shipping status updated successfully", TaxRead.model_validate(updated))