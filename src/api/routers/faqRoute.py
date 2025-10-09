# src/api/routes/faq.py
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
from src.api.models.faqModel import FAQ, FAQCreate, FAQUpdate, FAQRead

router = APIRouter(prefix="/faq", tags=["FAQ"])


# ✅ CREATE FAQ
@router.post("/create")
def create_faq(
    request: FAQCreate,
    session: GetSession,
    user=requirePermission("faq:create"),
):
    print("❓ Creating FAQ:", request.model_dump())

    # Check if FAQ with same question already exists
    existing_faq = session.exec(
        select(FAQ).where(FAQ.question == request.question)
    ).first()
    
    if existing_faq:
        return api_response(400, "FAQ with this question already exists")

    faq = FAQ(**request.model_dump())
    session.add(faq)
    session.commit()
    session.refresh(faq)

    return api_response(201, "FAQ created successfully", FAQRead.model_validate(faq))


# ✅ UPDATE FAQ
@router.put("/update/{id}")
def update_faq(
    id: int,
    request: FAQUpdate,
    session: GetSession,
    user=requirePermission("faq:update"),
):
    faq = session.get(FAQ, id)
    raiseExceptions((faq, 404, "FAQ not found"))

    # Check if question is being updated and if it already exists
    if request.question and request.question != faq.question:
        existing_faq = session.exec(
            select(FAQ).where(
                FAQ.question == request.question,
                FAQ.id != id
            )
        ).first()
        
        if existing_faq:
            return api_response(400, "Another FAQ with this question already exists")

    updated = updateOp(faq, request, session)
    session.commit()
    session.refresh(updated)

    return api_response(200, "FAQ updated successfully", FAQRead.model_validate(updated))


# ✅ READ FAQ BY ID
@router.get("/read/{id}")
def read_faq(id: int, session: GetSession):
    faq = session.get(FAQ, id)
    raiseExceptions((faq, 404, "FAQ not found"))

    return api_response(200, "FAQ found", FAQRead.model_validate(faq))


# ✅ DELETE FAQ
@router.delete("/delete/{id}")
def delete_faq(
    id: int,
    session: GetSession,
    user=requirePermission("faq:delete"),
):
    faq = session.get(FAQ, id)
    raiseExceptions((faq, 404, "FAQ not found"))

    session.delete(faq)
    session.commit()
    return api_response(200, f"FAQ deleted successfully")


# ✅ LIST ALL FAQS (Admin - with pagination and search)
@router.get("/list", response_model=list[FAQRead])
def list_faqs(
    query_params: ListQueryParams,
    user=requirePermission("faq:view_all")
):
    query_params = vars(query_params)
    searchFields = ["question", "answer"]
    
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=FAQ,
        Schema=FAQRead,
    )


# ✅ LIST ACTIVE FAQS (Public - ordered by order field)
@router.get("/active", response_model=list[FAQRead])
def list_active_faqs(session: GetSession):
    """Get all active FAQs ordered by order field (ascending)"""
    faqs = session.exec(
        select(FAQ)
        .where(FAQ.is_active == True)
        .order_by(FAQ.order.asc(), FAQ.created_at.desc())
    ).all()
    
    return [FAQRead.model_validate(faq) for faq in faqs]


# ✅ REORDER FAQS
@router.put("/reorder")
def reorder_faqs(
    reorder_data: dict,  # {faq_id: new_order}
    session: GetSession,
    user=requirePermission("faq:update"),
):
    try:
        for faq_id, new_order in reorder_data.items():
            faq = session.get(FAQ, int(faq_id))
            if faq:
                faq.order = new_order
        
        session.commit()
        return api_response(200, "FAQs reordered successfully")
    
    except Exception as e:
        session.rollback()
        return api_response(500, f"Error reordering FAQs: {str(e)}")


# ✅ BULK UPDATE FAQ STATUS
@router.put("/bulk-status")
def bulk_update_faq_status(
    update_data: dict,  # {faq_ids: [1,2,3], is_active: true/false}
    session: GetSession,
    user=requirePermission("faq:update"),
):
    try:
        faq_ids = update_data.get("faq_ids", [])
        is_active = update_data.get("is_active")
        
        if not faq_ids or is_active is None:
            return api_response(400, "Invalid data provided")
        
        for faq_id in faq_ids:
            faq = session.get(FAQ, faq_id)
            if faq:
                faq.is_active = is_active
        
        session.commit()
        action = "activated" if is_active else "deactivated"
        return api_response(200, f"FAQs {action} successfully")
    
    except Exception as e:
        session.rollback()
        return api_response(500, f"Error updating FAQ status: {str(e)}")


# ✅ SEARCH FAQS (Public)
@router.get("/search")
def search_faqs(
    query: str,
    session: GetSession,
    limit: int = 10
):
    """Search through active FAQs by question or answer"""
    if not query or len(query.strip()) < 2:
        return api_response(400, "Search query must be at least 2 characters long")
    
    search_query = f"%{query.strip()}%"
    
    faqs = session.exec(
        select(FAQ)
        .where(
            FAQ.is_active == True,
            (FAQ.question.ilike(search_query) | FAQ.answer.ilike(search_query))
        )
        .order_by(FAQ.order.asc(), FAQ.created_at.desc())
        .limit(limit)
    ).all()
    
    return api_response(
        200, 
        f"Found {len(faqs)} FAQs", 
        [FAQRead.model_validate(faq) for faq in faqs]
    )


# ✅ GET FAQ COUNT
@router.get("/count")
def get_faq_count(
    session: GetSession,
    user=requirePermission("faq:view_all")
):
    """Get count of all FAQs and active FAQs"""
    total_faqs = session.exec(select(FAQ)).all()
    active_faqs = session.exec(select(FAQ).where(FAQ.is_active == True)).all()
    
    return api_response(200, "FAQ counts retrieved", {
        "total": len(total_faqs),
        "active": len(active_faqs),
        "inactive": len(total_faqs) - len(active_faqs)
    })