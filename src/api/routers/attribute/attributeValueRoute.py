from fastapi import APIRouter
from sqlalchemy import select
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.attributes_model.attributeValueModel import (
    AttributeValue,
    AttributeValueCreate,
    AttributeValueRead,
    AttributeValueUpdate,
)
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)


router = APIRouter(prefix="/attribute_value", tags=["Attribute Value"])


@router.post("/create")
def create_role(
    request: AttributeValueCreate,
    session: GetSession,
    user=requirePermission("attribute"),
):
    attribute = AttributeValue(**request.model_dump())
    attribute.slug = uniqueSlugify(
        session,
        AttributeValue,
        attribute.value,
    )
    session.add(attribute)
    session.commit()
    session.refresh(attribute)
    return api_response(200, "AttributeValue Created Successfully", attribute)


@router.put("/update/{id}", response_model=AttributeValueRead)
def update_role(
    id: int,
    request: AttributeValueUpdate,
    session: GetSession,
    user=requirePermission("attribute"),
):
    attribute = session.get(AttributeValue, id)  # Like findById
    raiseExceptions((attribute, 404, "Attribute not found"))
    data = updateOp(attribute, request, session)

    if data.value:
        data.slug = uniqueSlugify(session, AttributeValue, data.value)
    session.commit()
    session.refresh(data)
    return api_response(200, "Attribute Update Successfully", data)


@router.get("/read/{id_slug}", description="Attribute ID (int) or slug (str)")
def get_role(id_slug: str, session: GetSession):
    attribute = None

    # Check if it's an integer ID
    if id_slug.isdigit():
        attribute = session.get(AttributeValue, int(id_slug))
    else:
        # Otherwise treat as slug
        attribute = (
            session.exec(
                select(AttributeValue).where(AttributeValue.slug.ilike(id_slug))
            )
            .scalars()
            .first()
        )

    raiseExceptions((attribute, 404, "Attribute not found"))
    return api_response(
        200, "attribute Found", AttributeValueRead.model_validate(attribute)
    )


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
@router.get("/list", response_model=list[AttributeValueRead])
def list(query_params: ListQueryParams, user: requireSignin):
    query_params = vars(query_params)
    searchFields = ["value"]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=AttributeValue,
        Schema=AttributeValueRead,
    )
