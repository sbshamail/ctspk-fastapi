from fastapi import APIRouter
from sqlalchemy import select, func
from typing import List
from sqlmodel import select
from src.api.models.category_model.categoryModel import Category
from src.api.models.product_model.variationOptionModel import VariationOption, VariationOptionCreate, VariationOptionUpdate
from src.api.core.middleware import handle_async_wrapper
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.models.product_model.productsModel import (
    Product,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ProductActivate,
    ProductType,
    VariationData,
    GroupedProductItem
)
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requirePermission,
    requireSignin,
)
from src.api.core.sku_generator import generate_unique_sku, generate_sku_for_variation
from sqlalchemy.orm import aliased

router = APIRouter(prefix="/product", tags=["Product"])


def create_variations_for_product(session, product_id: int, variations_data: List[VariationData], base_sku: str):
    """Create variation options for a variable product"""
    variations = []
    for index, var_data in enumerate(variations_data):
        # Create title from attributes
        attribute_names = []
        for attr in var_data.attributes:
            attr_name = attr.get('attribute_name', '')
            attr_value = attr.get('value', '')
            attribute_names.append(f"{attr_name}: {attr_value}")
        
        title = " - ".join(attribute_names)
        
        # Generate SKU for variation if not provided
        variation_sku = var_data.sku
        if not variation_sku:
            variation_sku = generate_sku_for_variation(
                session, 
                base_sku, 
                variation_suffix=f"V{index + 1:02d}"
            )
        
        variation = VariationOption(
            title=title,
            price=str(var_data.price),
            sale_price=str(var_data.sale_price) if var_data.sale_price else None,
            purchase_price=var_data.purchase_price,
            quantity=var_data.quantity,
            product_id=product_id,
            options={attr['attribute_name']: attr['value'] for attr in var_data.attributes},
            image=var_data.image,
            sku=variation_sku,
            bar_code=var_data.bar_code,
            is_active=var_data.is_active
        )
        session.add(variation)
        variations.append(variation)
    
    session.commit()
    return variations


# ✅ CREATE
@router.post("/create")
@handle_async_wrapper
def create(
    request: ProductCreate,
    session: GetSession,
    user=requirePermission("product_create", "shop_admin"),
):
    # Generate SKU if not provided
    if not request.sku:
        request.sku = generate_unique_sku(session)
    
    # Validate SKU format if provided
    if request.sku and not request.sku.startswith('SK-'):
        return api_response(400, "SKU must start with 'SK-' prefix")
    
    # Check if SKU already exists
    if request.sku:
        existing_product = session.exec(
            select(Product).where(Product.sku == request.sku)
        ).first()
        if existing_product:
            return api_response(400, "SKU already exists")
    
    # Calculate min and max prices
    if request.product_type == ProductType.SIMPLE:
        min_price = request.price
        max_price = request.price
    elif request.product_type == ProductType.VARIABLE and request.variations:
        prices = [var.price for var in request.variations]
        min_price = min(prices)
        max_price = max(prices)
    else:
        min_price = request.min_price or request.price
        max_price = request.max_price or request.price
    
    # Prepare product data
    product_data = request.model_dump(exclude={'attributes', 'variations', 'grouped_products'})
    product_data.update({
        'min_price': min_price,
        'max_price': max_price,
        'attributes': [attr.model_dump() for attr in request.attributes] if request.attributes else None,
        'grouped_products': [item.model_dump() for item in request.grouped_products] if request.grouped_products else None
    })
    
    data = Product(**product_data)
    data.slug = uniqueSlugify(session, Product, data.name)
    session.add(data)
    session.commit()
    session.refresh(data)
    
    # Create variations for variable products
    if request.product_type == ProductType.VARIABLE and request.variations:
        create_variations_for_product(session, data.id, request.variations, data.sku)
    
    return api_response(200, "Product Created Successfully", ProductRead.model_validate(data))


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

    # Validate SKU if provided
    if request.sku and not request.sku.startswith('SK-'):
        return api_response(400, "SKU must start with 'SK-' prefix")
    
    # Check if SKU already exists
    if request.sku and request.sku != updateData.sku:
        existing_product = session.exec(
            select(Product).where(Product.sku == request.sku)
        ).first()
        if existing_product:
            return api_response(400, "SKU already exists")

    # Prepare update data
    update_data = request.model_dump(exclude_none=True, exclude={'attributes', 'variations', 'grouped_products'})
    
    if request.attributes is not None:
        update_data['attributes'] = [attr.model_dump() for attr in request.attributes]
    
    if request.grouped_products is not None:
        update_data['grouped_products'] = [item.model_dump() for item in request.grouped_products]

    data = updateOp(updateData, ProductUpdate(**update_data), session)
    
    if data.name:
        data.slug = uniqueSlugify(session, Product, data.name)

    session.commit()
    session.refresh(data)
    
    return api_response(200, "Product Updated Successfully", ProductRead.model_validate(data))


@router.get(
    "/read/{id_slug}",
    description="Product ID (int) or slug (str)",
)
def get(id_slug: str, session: GetSession):
    # Check if it's an integer ID
    if id_slug.isdigit():
        read = session.get(Product, int(id_slug))
    else:
        # Otherwise treat as slug
        read = session.exec(select(Product).where(Product.slug.ilike(id_slug))).first()
    raiseExceptions((read, 404, "Product not found"))

    return api_response(200, "Product Found", ProductRead.model_validate(read))


# ✅ DELETE
@router.delete("/delete/{id}")
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


@router.get("/list")
def list(query_params: ListQueryParams, session: GetSession):
    try:
        # Simple list implementation without complex relationships
        statement = select(Product)
        products = session.exec(statement).all()
        
        return api_response(
            200,
            "Products found",
            [ProductRead.model_validate(p) for p in products],
            len(products)
        )
    except Exception as e:
        return api_response(500, f"Error fetching products: {str(e)}")


# ✅ PATCH Product status
@router.patch("/{id}/status")
def patch_product_status(
    id: int,
    request: ProductActivate,
    session: GetSession,
    user=requirePermission(["system:*", "shop_admin"]),
):
    product = session.get(Product, id)
    raiseExceptions((product, 404, "Product not found"))

    updated = updateOp(product, request, session)
    session.add(updated)
    session.commit()
    session.refresh(updated)

    return api_response(200, "Product status updated successfully", ProductRead.model_validate(updated))