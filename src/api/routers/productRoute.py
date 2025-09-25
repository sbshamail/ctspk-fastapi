from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

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


@router.get("/list", response_model=list[ProductRead])
def list(
    query_params: ListQueryParams,
):
    query_params = vars(query_params)
    searchFields = ["name", "description", "category.name"]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
    )
