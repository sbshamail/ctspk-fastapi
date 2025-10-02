from fastapi import APIRouter
from sqlalchemy import select
from src.api.core.utility import slugify, uniqueSlugify
from src.api.core.middleware.decorator import handle_async_wrapper
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.email_model import (
    Emailtemplate,
    EmailCreate,
    EmailUpdate,
    EmailRead,
    EmailActivate
)
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)


router = APIRouter(prefix="/email", tags=["Emailtemplate"])


@router.post("/create")
def create_role(
    request: EmailCreate,
    session: GetSession,
    user=requirePermission("system:*"),
):
    email = sh(**request.model_dump())
    email.slug = uniqueSlugify(
        session,
        Emailtemplate,
        email.name,
    )
    session.add(email)
    session.commit()
    session.refresh(email)
    return api_response(200, "Email Created Successfully", email)


@router.put("/update/{id}", response_model=EmailRead)
def update_role(
    id: int,
    request: EmailUpdate,
    session: GetSession,
    user=requirePermission("system:*"),
):
    email = session.get(Emailtemplate, id)  # Like findById
    raiseExceptions((email, 404, "Email not found"))
    data = updateOp(email, request, session)

    if data.name:
        data.slug = uniqueSlugify(session, Emailtemplate, data.name)
    session.commit()
    session.refresh(data)
    return api_response(200, "Emailtemplate Update Successfully", data)


@router.get("/read/{id_slug}", description="Emailtemplate ID (int) or slug (str)")
def get_role(id_slug: str, session: GetSession):
    email = None

    # Check if it's an integer ID
    if id_slug.isdigit():
        email = session.get(Emailtemplate, int(id_slug))
    else:
        # Otherwise treat as slug
        email = (
            session.exec(select(Emailtemplate).where(Emailtemplate.slug.ilike(id_slug)))
            .scalars()
            .first()
        )

    raiseExceptions((email, 404, "Email not found"))
    return api_response(
        200, "Shipping Found", EmailRead.model_validate(email)
    )


# ❗ DELETE
@router.delete("/delete/{id}", response_model=dict)
def delete_role(
    id: int,
    session: GetSession,
    user=requirePermission("system:*"),
):
    email = session.get(Emailtemplate, id)
    raiseExceptions((shipping, 404, "Email not found"))

    session.delete(email)
    session.commit()
    return api_response(404, f"Email {email.id} deleted")


# ✅ LIST
@router.get("/list", response_model=list[EmailRead])
def list(query_params: ListQueryParams, user: requireSignin):
    query_params = vars(query_params)
    searchFields = []
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Emailtemplate,
        Schema=EmailRead,
    )

# ✅ PATCH Emailtemplate status (toggle/verify)
@router.patch("/{id}/status")
def patch_email_status(
    id: int,
    request: EmailActivate,
    session: GetSession,
    user=requirePermission(["system:*"]),  # 🔒 both allowed
):
    email = session.get(Emailtemplate, id)
    raiseExceptions((email, 404, "Email not found"))

    # only update status fields
    updated = updateOp(email, request, session)

    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Email status updated successfully", EmailRead.model_validate(updated))
