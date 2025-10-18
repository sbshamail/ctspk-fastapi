from fastapi import APIRouter
from sqlalchemy import select
from src.api.models.attributes_model.attributeValueModel import AttributeValue
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


# @router.post("/create")
# def create_role(
#     request: AttributeCreate,
#     session: GetSession,
#     user=requirePermission("attribute"),
# ):
#     attribute = Attribute(**request.model_dump())
#     attribute.slug = uniqueSlugify(
#         session,
#         Attribute,
#         attribute.name,
#     )
#     session.add(attribute)
#     session.commit()
#     session.refresh(attribute)
#     return api_response(200, "Attribute Created Successfully", attribute)


@router.post("/create")
def create_attribute(
    request: AttributeCreate,
    session: GetSession,
    user=requirePermission("attribute"),
):
    try:
        with session.begin():  # <-- Transaction starts here

            # Step 1: Create Attribute
            attribute = Attribute(
                name=request.name,
                language=request.language,
            )
            attribute.slug = uniqueSlugify(
                session,
                Attribute,
                attribute.name,
            )
            session.add(attribute)
            session.flush()  # ensures attribute.id is available before commit

            # Step 2: Create Attribute Values (if provided)
            if request.values:
                for val in request.values:
                    attr_value = AttributeValue(
                        slug=uniqueSlugify(session, AttributeValue, val.value),
                        attribute_id=attribute.id,
                        value=val.value,
                        language=getattr(val, "language", "en"),
                        meta=getattr(val, "meta", None),
                    )
                    session.add(attr_value)

        # 🚀 At this point, commit happens automatically if no error occurred
        session.refresh(attribute)
        return api_response(
            200,
            "Attribute Created Successfully",
            AttributeRead.model_validate(attribute),
        )

    except Exception as e:
        session.rollback()  # rollback if error
        raise e

@router.put("/update/{id}")
def update_attribute(
    id: int,
    request: AttributeUpdate,
    session: GetSession,
    user=requirePermission("attribute"),
):
    try:
        with session.begin():
            # Step 1: Find and update Attribute
            attribute = session.get(Attribute, id)
            raiseExceptions((attribute, 404, "Attribute not found"))
            
            # Update attribute fields
            if request.name:
                attribute.name = request.name
                attribute.slug = uniqueSlugify(session, Attribute, request.name)
            if request.language:
                attribute.language = request.language
            
            session.flush()

            # Step 2: Handle Attribute Values update
            if request.values is not None:
                # Get existing values
                existing_values = session.query(AttributeValue).filter(
                    AttributeValue.attribute_id == attribute.id
                ).all()
                
                existing_value_map = {val.id: val for val in existing_values}
                processed_value_ids = set()
                
                # Process all values from request
                for val_request in request.values:
                    # Check if this is an existing value (has id and id is not None)
                    if val_request.id is not None:
                        value_id = val_request.id
                        if value_id in existing_value_map:
                            # Update existing value
                            existing_val = existing_value_map[value_id]
                            if val_request.value:
                                existing_val.value = val_request.value
                                existing_val.slug = uniqueSlugify(session, AttributeValue, val_request.value)
                            if val_request.language:
                                existing_val.language = val_request.language
                            if val_request.meta is not None:
                                existing_val.meta = val_request.meta
                            processed_value_ids.add(value_id)
                    else:
                        # 🆕 ADD NEW VALUE - when no ID is provided
                        attr_value = AttributeValue(
                            slug=uniqueSlugify(session, AttributeValue, val_request.value),
                            attribute_id=attribute.id,
                            value=val_request.value,
                            language=val_request.language or "en",
                            meta=val_request.meta,
                        )
                        session.add(attr_value)
                
                # Delete values that are not in the incoming request
                for existing_val in existing_values:
                    if existing_val.id not in processed_value_ids:
                        session.delete(existing_val)

        session.refresh(attribute)
        return api_response(
            200,
            "Attribute Updated Successfully",
            AttributeRead.model_validate(attribute),
        )

    except Exception as e:
        session.rollback()
        raise e

# @router.put("/update/{id}", response_model=AttributeRead)
# def update_role(
#     id: int,
#     request: AttributeUpdate,
#     session: GetSession,
#     user=requirePermission("attribute"),
# ):
#     attribute = session.get(Attribute, id)  # Like findById
#     raiseExceptions((attribute, 404, "Attribute not found"))
#     data = updateOp(attribute, request, session)

#     if data.name:
#         data.slug = uniqueSlugify(session, Attribute, data.name)
#     session.commit()
#     session.refresh(data)
#     return api_response(200, "Attribute Update Successfully", data)


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
