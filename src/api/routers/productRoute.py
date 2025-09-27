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
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requirePermission,
    requireSignin,
)
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

    shop_ids = [s["id"] for s in user.get("shops", [])]
    if updateData.shop_id not in shop_ids:
        return api_response(403, "You are not the user of this Product")

    updateOp(updateData, request, session)

    session.commit()
    session.refresh(updateData)
    return api_response(
        200, "Product Updated Successfully", ProductRead.model_validate(updateData)
    )


@router.put("/update_by_admin/{id}")
def update(
    id: int,
    request: ProductUpdate,
    session: GetSession,
    user=requirePermission("admin"),
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


@router.get("/list", response_model=list[ProductRead])
def list(query_params: ListQueryParams):
    query_params = vars(query_params)
    searchFields = ["name", "description", "category.name"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
    )


@router.get("/products/related/{category_id}")
def get_products_by_category(category_id: int, session: GetSession):
    try:
        # Get all descendant category IDs (recursively)
        def get_descendants(cat_id: int):
            q = session.exec(select(Category).where(Category.parent_id == cat_id)).all()
            ids = [cat.id for cat in q]
            for c in q:
                ids.extend(get_descendants(c.id))
            return ids

        # include self
        category_ids = [category_id] + get_descendants(category_id)

        # Fetch products belonging to any of those categories
        stmt = select(Product).where(Product.category_id.in_(category_ids))
        products = session.exec(stmt).all()
        # return {"products": [ProductRead.model_validate(p) for p in products]}
        return api_response(
            200,
            "found product",
            [ProductRead.model_validate(p) for p in products],
            len(products),
        )
    finally:
        session.close()
