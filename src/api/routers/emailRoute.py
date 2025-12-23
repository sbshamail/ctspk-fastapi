from typing import Optional
from fastapi import APIRouter, Query
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
    EmailActivate,
    EmailDuplicate   # NEW: Import the duplicate model
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
     # Debug print
    print("📦 Incoming request:", request.model_dump())
    #return
    email = Emailtemplate(**request.model_dump())
    print(email.__dict__)
   # return api_response(404, "Shipping not found", email)  # 👈 always returning 404 here!
    email.slug = uniqueSlugify(
        session,
        Emailtemplate,
        email.name,
    )
    session.add(email)
    session.commit()
    session.refresh(email)
    return api_response(200, "Email Created Successfully", EmailRead.model_validate(email))


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
        200, "Email Found", EmailRead.model_validate(email)  # FIXED: Changed "Shipping" to "Email"
    )


# ❗ DELETE
@router.delete("/delete/{id}", response_model=dict)
def delete_role(
    id: int,
    session: GetSession,
    user=requirePermission("system:*"),
):
    email = session.get(Emailtemplate, id)
    raiseExceptions((email, 404, "Email not found"))  # FIXED: Changed "shipping" to "email"

    session.delete(email)
    session.commit()
    return api_response(200, f"Email {email.id} deleted")  # FIXED: Changed status code from 404 to 200


# ✅ LIST
@router.get("/list", response_model=list[EmailRead])
def list(
    query_params: ListQueryParams,
    user: requireSignin,
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

# NEW: Duplicate email template route
@router.post("/duplicate/{id}")
def duplicate_email(
    id: int,
    request: EmailDuplicate,
    session: GetSession,
    user=requirePermission("system:*"),
):
    # Get the original email template
    email = session.get(Emailtemplate, id)
    raiseExceptions((email, 404, "Original email template not found"))
    
    # Create a copy of the original template data
    email_data = {
        "name": request.new_name,
        "subject": email.subject,
        "is_active": request.is_active,
        "language": email.language
    }
    
    # Copy content if requested
    if request.copy_content:
        email_data["content"] = email.content
        email_data["html_content"] = email.html_content
    
    # Create new email template instance
    new_email = Emailtemplate(**email_data)
    
    # Generate unique slug for the new template
    new_email.slug = uniqueSlugify(
        session,
        Emailtemplate,
        request.new_name,
    )
    
    # Save to database
    session.add(new_email)
    session.commit()
    session.refresh(new_email)
    
    return api_response(
        200, 
        "Email template duplicated successfully", 
        EmailRead.model_validate(new_email)
    )