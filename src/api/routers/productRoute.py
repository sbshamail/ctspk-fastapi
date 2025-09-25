from typing import List, Optional
from fastapi import APIRouter, Query
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from src.api.models.category_model.categoryModel import Category
from src.api.core.middleware import handle_async_wrapper
from src.api.core.utility import Print
from src.api.core.operation import listRecords, listop, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.product_model.productsModel import (
    Product,
    ProductCreate,
    ProductRead,
    ProductUpdate,
)
from src.api.core.dependencies import GetSession, ListQueryParams, requirePermission
from sqlalchemy.orm import aliased

router = APIRouter(prefix="/product", tags=["Product"])


# ✅ CREATE
@router.post("/create")
@handle_async_wrapper
def create(
    request: ProductCreate,
    session: GetSession,
    user=requirePermission("product_create", "shop_admin"),
):
    data = Product(**request.model_dump())
    Print(data)
    session.add(data)
    session.commit()
    session.refresh(data)
    return api_response(
        200, "Product Created Successfully", ProductRead.model_validate(data)
    )


# ✅ UPDATE
@router.put("/update/{id}")
def update(
    id: int,
    request: ProductUpdate,
    session: GetSession,
    user=requirePermission("product_create"),
):
    updateData = session.get(Product, id)
    raiseExceptions((updateData, 404, "Product not found"))

    updateOp(updateData, request, session)

    session.commit()
    session.refresh(updateData)
    return api_response(
        200, "Product Updated Successfully", ProductRead.model_validate(updateData)
    )


# ✅ READ (single)
@router.get("/read/{id}", response_model=ProductRead)
def get(id: int, session: GetSession):
    read = session.get(Product, id)
    raiseExceptions((read, 404, "Product not found"))

    return api_response(200, "Product Found", ProductRead.model_validate(read))


# ✅ DELETE
@router.delete("/delete/{id}", response_model=dict)
def delete(
    id: int,
    session: GetSession,
    user=requirePermission("product-delete"),
):
    product = session.get(Product, id)
    raiseExceptions((product, 404, "Product not found"))

    session.delete(product)
    session.commit()
    return api_response(200, f"Product {product.name} deleted")


from sqlmodel import select
from sqlalchemy import union_all


def categoryFilter(
    session, category_id: int | List[int] = None, slug: str | List[str] = None
):
    def _get_descendants(start_ids: List[int]):
        cats = Category.__table__
        initial = select(cats.c.id, cats.c.parent_id).where(cats.c.id.in_(start_ids))
        cte = initial.cte(name="category_cte", recursive=True)
        recursive = select(cats.c.id, cats.c.parent_id).where(
            cats.c.parent_id == cte.c.id
        )
        cte = cte.union_all(recursive)
        ids = session.exec(select(cte.c.id)).all()
        return [r[0] for r in ids]

    # resolve root ids
    root_ids: List[int] = []
    if category_id:
        if not isinstance(category_id, (list, tuple)):
            category_id = [category_id]
        root_ids.extend(int(x) for x in category_id)

    if slug:
        if not isinstance(slug, (list, tuple)):
            slug = [slug]
        rows = session.exec(select(Category.id).where(Category.slug.in_(slug))).all()
        root_ids.extend(r[0] for r in rows)

    target_ids = _get_descendants(root_ids) if root_ids else []

    def _filter(statement, Model):
        if not target_ids:
            return statement.where(text("1=0"))  # force empty
        if hasattr(Model, "category_id"):
            return statement.where(
                Model.category_id.in_(target_ids)
            )  # ✅ use IN, not =
        return statement

    return _filter


@router.get("/list", response_model=list[ProductRead])
def list(query_params: ListQueryParams, session: GetSession):
    query_params = vars(query_params)
    searchFields = ["name", "description", "category.name"]
    cat_id = query_params.get("category_id")
    cat_slug = query_params.get("category_slug")
    otherFilters = None
    if cat_id or cat_slug:
        otherFilters = categoryFilter(session, category_id=cat_id, slug=cat_slug)
        print("=================================>", otherFilters)

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
        otherFilters=otherFilters,
    )


@router.get("/related")
def get_descendant_category_ids(session: GetSession, category_id: int) -> List[int]:
    base = select(Category).where(Category.id == category_id)
    category_cte = base.cte(name="category_tree", recursive=True)

    cat_alias = aliased(Category)
    recursive = select(cat_alias).where(cat_alias.parent_id == category_cte.c.id)
    category_cte = category_cte.union_all(recursive)

    stmt = select(category_cte.c.id)
    ids = session.exec(stmt).all()
    return [row[0] for row in ids]  # list of IDs


def get_products_by_category(session, category_id: int):
    category_ids = get_descendant_category_ids(session, category_id)

    stmt = select(Product).where(Product.category_id.in_(category_ids))
    return session.exec(stmt).all()
