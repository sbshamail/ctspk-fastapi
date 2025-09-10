from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select
from src.api.core.utility import Print
from src.api.core.operation import listop, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.categoryModel import (
    Category,
    CategoryCreate,
    CategoryRead,
    CategoryReadNested,
    CategoryUpdate,
)
from src.api.core.dependencies import GetSession, requirePermission
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/category", tags=["Category"])


@router.post("/create")
def create(
    request: CategoryCreate, session: GetSession, user=requirePermission("category")
):
    data = Category(**request.model_dump())
    Print(data, "data")
    session.add(data)
    session.commit()
    session.refresh(data)
    return api_response(
        200, "Category Created Successfully", CategoryRead.model_validate(data)
    )


@router.put("/update/{id}")
def update(
    id: int,
    request: CategoryUpdate,
    session: GetSession,
    user=requirePermission("category"),
):

    updateData = session.get(Category, id)  # Like findById
    raiseExceptions((updateData, 404, "Category not found"))
    updateOp(updateData, request, session)

    session.commit()
    session.refresh(updateData)
    return api_response(
        200,
        "Category Update Successfully",
        CategoryReadNested.model_validate(updateData),
    )


@router.get("/read/{id}", response_model=CategoryReadNested)
def get(
    id: int,
    session: GetSession,
    user=requirePermission("category"),
):

    read = session.get(Category, id)  # Like findById
    raiseExceptions((read, 404, "Category not found"))

    return api_response(200, "Category Found", CategoryReadNested.model_validate(read))


# ❗ DELETE
@router.delete("/delete/{id}", response_model=dict)
def delete(
    id: int,
    session: GetSession,
    user=requirePermission("category-delete"),
):
    category = session.get(Category, id)
    raiseExceptions((category, 404, "category not found"))

    children = session.exec(select(Category).where(Category.parent_id == id)).all()
    raiseExceptions(
        (
            len(children) > 0,
            400,
            f"Cannot delete category '{category.title}' because it has child categories.",
            True,
        )
    )
    session.delete(category)
    session.commit()
    return api_response(404, f"Category {category.title} deleted")


def delete_category_tree(session, category_id: int):
    """
    Recursively delete a category and all its children.
    """
    # Get all direct children
    children = (
        session.exec(select(Category).where(Category.parent_id == category_id))
        .scalars()
        .all()
    )

    # Recursively delete children first
    for child in children:
        print("+++++++++++++++++++++++++", child)
        delete_category_tree(session, child.id)

    # Finally delete this category
    category = session.get(Category, category_id)
    if category:
        session.delete(category)


@router.delete("/delete-parent/{id}")
def deleteMany(
    id: int,
    session: GetSession,
    user=requirePermission("category-delete"),
):
    category = session.get(Category, id)
    raiseExceptions((category, 404, "category not found"))
    # Recursively delete this category and all its children
    delete_category_tree(session, id)
    session.commit()

    return api_response(
        200, f"Category tree with root {category.title} deleted successfully"
    )


# ✅ LIST
@router.get("/list", response_model=list[CategoryReadNested])
def list(
    session: GetSession,
    dateRange: Optional[
        str
    ] = None,  # JSON string like '["created_at", "01-01-2025", "01-12-2025"]'
    numberRange: Optional[str] = None,  # JSON string like '["amount", "0", "100000"]'
    searchTerm: str = None,
    columnFilters: Optional[str] = Query(
        None
    ),  # e.g. '[["name","car"],["description","product"]]'
    page: int = None,
    skip: int = 0,
    limit: int = Query(10, ge=1, le=100),
    user=requirePermission("category"),
):
    filters = {
        "searchTerm": searchTerm,
        "columnFilters": columnFilters,
        "dateRange": dateRange,
        "numberRange": numberRange,
        # "customFilters": customFilters,
    }
    searchFields = [
        "title",
    ]

    result = listop(
        session=session,
        Model=Category,
        searchFields=searchFields,
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
        join_options=[selectinload(Category.children)],
    )
    if not result["data"]:
        return api_response(404, "No products found")
    categories = result["data"]
    # assuming your search result is in `categories`
    # Treat the first search result as root by ignoring its parent
    if categories and categories[0].parent_id:
        categories[0].parent_id = None
    category_map = {
        c.id: CategoryReadNested(
            id=c.id,
            title=c.title,
            description=c.description,
            parent_id=c.parent_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
            children=[],
        )
        for c in categories
    }
    roots = []

    # Step 1: attach children
    for cat in category_map.values():
        if cat.parent_id and cat.id != cat.parent_id:  # has a parent
            parent = category_map.get(cat.parent_id)
            if parent:
                if not any(child.id == cat.id for child in parent.children):
                    parent.children.append(cat)
        # ❌ DO NOT append to roots here

    # Step 2: collect only roots
    for cat in category_map.values():
        if not cat.parent_id:  # no parent_id means it's a root
            roots.append(cat)

    return api_response(200, "Category found", roots, result["total"])
