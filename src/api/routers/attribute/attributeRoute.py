from fastapi import APIRouter
from sqlalchemy import select
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.attributes_model import (
    Attribute,
    AttributeCreate,
    AttributeRead,
    AttributeUpdate,
)
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)


router = APIRouter(prefix="/attribute", tags=["Attribute"])


@router.post("/create")
def create_role(
    request: AttributeCreate,
    session: GetSession,
    user=requirePermission("attribute"),
):
    attribute = Attribute(**request.model_dump())
    attribute.slug = uniqueSlugify(
        session,
        Attribute,
        attribute.name,
    )
    session.add(attribute)
    session.commit()
    session.refresh(attribute)
    return api_response(200, "Attribute Created Successfully", attribute)


@router.put("/update/{id}", response_model=AttributeRead)
def update_role(
    id: int,
    request: AttributeUpdate,
    session: GetSession,
    user=requirePermission("attribute"),
):
    attribute = session.get(Attribute, id)  # Like findById
    raiseExceptions((attribute, 404, "Attribute not found"))
    data = updateOp(attribute, request, session)

    if data.name:
        data.slug = uniqueSlugify(session, Attribute, data.name)
    session.commit()
    session.refresh(data)
    return api_response(200, "Attribute Update Successfully", data)


@router.get("/read/{id_slug}", description="Attribute ID (int) or slug (str)")
def get_role(id_slug: str, session: GetSession):
    attribute = None

    # Check if it's an integer ID
    if id_slug.isdigit():
        attribute = session.get(Attribute, int(id_slug))
    else:
        # Otherwise treat as slug
        attribute = (
            session.exec(select(Attribute).where(Attribute.slug.ilike(id_slug)))
            .scalars()
            .first()
        )

    raiseExceptions((attribute, 404, "Attribute not found"))
    return api_response(200, "attribute Found", AttributeRead.model_validate(attribute))


# ❗ DELETE
@router.delete("/delete/{id}", response_model=dict)
def delete_role(
    id: int,
    session: GetSession,
    user=requirePermission("attribute"),
):
    attribute = session.get(attribute, id)
    raiseExceptions((attribute, 404, "attribute not found"))

    session.delete(attribute)
    session.commit()
    return api_response(404, f"attribute {attribute.id} deleted")


# ✅ LIST
@router.get("/list", response_model=list[AttributeRead])
def list(query_params: ListQueryParams, user: requireSignin):
    query_params = vars(query_params)
    searchFields = []
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Attribute,
        Schema=AttributeRead,
    )
