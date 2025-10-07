import ast
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select
from src.api.core.utility import Print, uniqueSlugify
from src.api.core.operation import listop, updateOp
from src.api.core.response import api_response, raiseExceptions
from sqlalchemy.orm import aliased
from src.api.models.category_model.categoryModel import (
    Category,
    CategoryCreate,
    CategoryRead,
    CategoryReadNested,
    CategoryUpdate,
    CategoryActivate,
)
from src.api.core.dependencies import GetSession, requirePermission
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/category", tags=["Category"])


def calculate_category_level(session, parent_id: Optional[int]) -> int:
    if not parent_id:
        return 1  # root level

    parent = session.get(Category, parent_id)
    if not parent:
        return api_response(400, "Parent category not found")

    if parent.level >= 3:
        return api_response(400, "Cannot create a category deeper than 3 levels")

    return parent.level + 1


@router.post("/create")
def create(
    request: CategoryCreate, session: GetSession, user=requirePermission("category")
):
    """Create a new category with auto-level and root assignment."""
    # 1️⃣ Calculate hierarchical level
    level = calculate_category_level(session, request.parent_id)
    # 2️⃣ Initialize model
    data = Category(**request.model_dump(), level=level)

    # 3️⃣ Generate unique slug
    data.slug = uniqueSlugify(session, Category, data.name)

    # add to session
    session.add(data)
    session.flush()  # assigns 'id' without committing

    # 4️⃣ Determine root_id
    if data.parent_id is None:
        data.root_id = data.id  # top-level category
    else:
        parent = session.get(Category, data.parent_id)
        data.root_id = parent.root_id if parent.root_id else parent.id

        # Top-level root fix
    if data.root_id is None:
        data.root_id = data.id

    session.commit()  # commit everything in one transaction
    session.refresh(data)

    return api_response(
        200, "Category Created Successfully", CategoryRead.model_validate(data)
    )


@router.put("/update/{id}")
def update_category(
    id: int,
    request: CategoryUpdate,
    session: GetSession,
    user=requirePermission("category"),
):
    """Update category safely, preserving tree structure."""
    category = session.get(Category, id)
    raiseExceptions((category, 404, "Category not found"))

    # Check if parent changed
    if request.parent_id is not None and request.parent_id != category.parent_id:
        # Cannot set parent to itself or its children
        if request.parent_id == id:
            api_response(400, "A category cannot be its own parent")

        # Verify parent validity
        parent = session.get(Category, request.parent_id)
        if not parent:
            api_response(400, "New parent category not found")

        if parent.level >= 3:
            api_response(400, "Cannot move under a level 3 category")

        # ✅ Update level and root based on new parent
        category.level = parent.level + 1
        category.root_id = parent.root_id if parent.root_id else parent.id
        category.parent_id = request.parent_id

    # Apply other updates dynamically
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(category, key, value)

    # Slug update if name changed
    if request.name:
        category.slug = uniqueSlugify(session, Category, request.name)
        category.updated_at = datetime.now(timezone.utc)

    session.add(category)
    session.commit()
    session.refresh(category)

    return api_response(
        200, "Category updated successfully", CategoryRead.model_validate(category)
    )


@router.get(
    "/read/{id_slug}",
    description="Category ID (int) or slug (str)",
    response_model=CategoryReadNested,
)
def get(id_slug: str, session: GetSession):
    # Check if it's an integer ID
    if id_slug.isdigit():
        read = session.get(Category, int(id_slug))
    else:
        # Otherwise treat as slug
        read = (
            session.exec(select(Category).where(Category.slug.ilike(id_slug)))
            .scalars()
            .first()
        )
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
    if category is None:
        return api_response(404, "Category not found")

    children = session.exec(select(Category).where(Category.parent_id == id)).all()
    raiseExceptions(
        (
            len(children) > 0,
            400,
            f"Cannot delete category '{category.name}' because it has child categories.",
            True,
        )
    )
    session.delete(category)
    session.commit()
    return api_response(200, f"Category {category.name} deleted")


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
        200, f"Category tree with root {category.name} deleted successfully"
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
    limit: int = Query(200, ge=1, le=200),
):

    filters = {
        "searchTerm": searchTerm,
        "columnFilters": columnFilters,
        "dateRange": dateRange,
        "numberRange": numberRange,
        # "customFilters": customFilters,
    }
    searchFields = [
        "name",
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
            name=c.name,
            image=c.image,
            root_id=c.root_id,
            slug=c.slug,
            details=c.details,
            is_active=c.is_active,
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


# ✅ PATCH Category status (toggle/verify)
@router.patch("/{id}/status")
def patch_category_status(
    id: int,
    request: CategoryActivate,
    session: GetSession,
    user=requirePermission(["system:*"]),  # 🔒 both allowed
):
    category = session.get(Category, id)
    raiseExceptions((category, 404, "Product not found"))

    # only update status fields
    updated = updateOp(category, request, session)

    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(
        200,
        "Category status updated successfully",
        CategoryRead.model_validate(updated),
    )
