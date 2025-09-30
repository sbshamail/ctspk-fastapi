from fastapi import APIRouter
from sqlalchemy import select
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.attributes_model.attributeProductModel import (
    AttributeProduct,
    AttributeProductCreate,
    AttributeProductRead,
    AttributeProductUpdate,
)
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)


router = APIRouter(prefix="/attribute_product", tags=["Attribute Product"])


@router.post("/create")
def create_role(
    request: AttributeProductCreate,
    session: GetSession,
    user=requirePermission("attribute"),
):
    attribute = AttributeProduct(**request.model_dump())

    session.add(attribute)
    session.commit()
    session.refresh(attribute)
    return api_response(200, "AttributeProduct Created Successfully", attribute)


@router.put("/update/{id}", response_model=AttributeProductRead)
def update_role(
    id: int,
    request: AttributeProductUpdate,
    session: GetSession,
    user=requirePermission("attribute"),
):
    attribute = session.get(AttributeProduct, id)  # Like findById
    raiseExceptions((attribute, 404, "Attribute not found"))
    data = updateOp(attribute, request, session)

    session.commit()
    session.refresh(data)
    return api_response(200, "Attribute Update Successfully", data)


@router.get("/read/{id_slug}", description="Attribute ID (int) or slug (str)")
def get_role(id_slug: str, session: GetSession):
    attribute = None

    # Check if it's an integer ID
    if id_slug.isdigit():
        attribute = session.get(AttributeProduct, int(id_slug))
    else:
        # Otherwise treat as slug
        attribute = (
            session.exec(
                select(AttributeProduct).where(AttributeProduct.slug.ilike(id_slug))
            )
            .scalars()
            .first()
        )

    raiseExceptions((attribute, 404, "Attribute not found"))
    return api_response(
        200, "attribute Found", AttributeProductRead.model_validate(attribute)
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
@router.get("/list", response_model=list[AttributeProductRead])
def list(query_params: ListQueryParams, user: requireSignin):
    query_params = vars(query_params)
    searchFields = ["value"]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=AttributeProduct,
        Schema=AttributeProductRead,
    )
