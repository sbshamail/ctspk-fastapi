from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.banner_model import Banner, BannerCreate, BannerRead, BannerUpdate,BannerActivate
from src.api.core.dependencies import GetSession, ListQueryParams, requirePermission


router = APIRouter(prefix="/banner", tags=["Banner"])


@router.post("/create")
def create_role(
    request: BannerCreate,
    session: GetSession,
    user=requirePermission("banner"),
):
    banner = Banner(**request.model_dump())
    banner.slug = uniqueSlugify(
        session,
        Banner,
        banner.name,
    )
    session.add(banner)
    session.commit()
    session.refresh(banner)
    return api_response(
        200, "Banner Created Successfully", BannerRead.model_validate(banner)
    )


@router.put("/update/{id}", response_model=BannerRead)
def update_role(
    id: int,
    request: BannerUpdate,
    session: GetSession,
    user=requirePermission("banner"),
):
    banner = session.get(Banner, id)  # Like findById
    raiseExceptions((banner, 404, "Banner not found"))
    data = updateOp(banner, request, session)
    if data.name:
        data.slug = uniqueSlugify(session, Banner, data.name)
    session.commit()
    session.refresh(banner)
    return api_response(
        200, "Banner Update Successfully", BannerRead.model_validate(banner)
    )


@router.get("/read/{id_slug}", description="Banner ID (int) or slug (str)")
def get_role(
    id_slug: str,
    session: GetSession,
):

    # Check if it's an integer ID
    if id_slug.isdigit():
        banner = session.get(Banner, int(id_slug))
    else:
        # Otherwise treat as slug
        banner = (
            session.exec(select(Banner).where(Banner.slug.ilike(id_slug)))
            .scalars()
            .first()
        )
    raiseExceptions((banner, 404, "Banner not found"))

    return api_response(200, "Banner Found", BannerRead.model_validate(banner))


# ❗ DELETE
@router.delete("/delete/{id}", response_model=dict)
def delete_role(
    id: int,
    session: GetSession,
    user=requirePermission("banner"),
):
    banner = session.get(Banner, id)
    raiseExceptions((banner, 404, "Banner not found"))

    session.delete(banner)
    session.commit()
    return api_response(404, f"Banner {banner.id} deleted")


# ✅ LIST
@router.get("/list", response_model=list[BannerRead])
def list(
    query_params: ListQueryParams,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    query_params = vars(query_params)

    # Add is_active to customFilters if provided
    if is_active is not None:
        query_params["customFilters"] = [["is_active", is_active]]

    searchFields = []
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Banner,
        Schema=BannerRead,
    )
# ✅ PATCH Banner status (toggle/verify)
@router.patch("/{id}/status")
def patch_banner_status(
    id: int,
    request: BannerActivate,
    session: GetSession,
    user=requirePermission(["system:*"]),  # 🔒 both allowed
):
    banner = session.get(Banner, id)
    raiseExceptions((banner, 404, "Banner not found"))

    # only update status fields
    updated = updateOp(banner, request, session)

    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Banner status updated successfully", BannerRead.model_validate(updated))