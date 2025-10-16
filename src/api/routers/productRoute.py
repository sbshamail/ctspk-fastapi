from fastapi import APIRouter
from sqlalchemy import select, func
from typing import List, Dict, Optional
from sqlmodel import select
from src.api.models.category_model.categoryModel import Category
from src.api.models.product_model.variationOptionModel import (
    VariationOption,
    VariationOptionCreate,
    VariationOptionUpdate,
)
from src.api.core.middleware import handle_async_wrapper
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.utils.video_processor import VideoProcessor
from src.api.models.product_model.productsModel import (
    Product,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ProductActivate,
    ProductType,
    ProductStatus,
    VariationData
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


def create_variations_for_product(
    session, product_id: int, variations_data: List[VariationData], base_sku: str
):
    """Create variation options for a variable product"""
    variations = []
    for index, var_data in enumerate(variations_data):
        # Create title from attributes
        attribute_names = []
        for attr in var_data.attributes:
            attr_name = attr.get("attribute_name", "")
            attr_value = attr.get("value", "")
            attribute_names.append(f"{attr_name}: {attr_value}")

        title = " - ".join(attribute_names)

        # Generate SKU for variation if not provided
        variation_sku = var_data.sku
        if not variation_sku:
            variation_sku = generate_sku_for_variation(
                session, base_sku, variation_suffix=f"V{index + 1:02d}"
            )

        variation = VariationOption(
            title=title,
            price=str(var_data.price),
            sale_price=str(var_data.sale_price) if var_data.sale_price else None,
            purchase_price=var_data.purchase_price,
            quantity=var_data.quantity,
            product_id=product_id,
            options={
                attr["attribute_name"]: attr["value"] for attr in var_data.attributes
            },
            image=var_data.image,
            sku=variation_sku,
            bar_code=var_data.bar_code,
            is_active=var_data.is_active,
        )
        session.add(variation)
        variations.append(variation)

    session.commit()
    return variations


def update_variations_for_product(
    session, product_id: int, variations_data: List[VariationData], base_sku: str
):
    """Update variation options for a variable product"""
    # Delete existing variations
    existing_variations = session.exec(
        select(VariationOption).where(VariationOption.product_id == product_id)
    ).all()

    for variation in existing_variations:
        session.delete(variation)

    session.commit()

    # Create new variations
    return create_variations_for_product(session, product_id, variations_data, base_sku)


def get_product_with_enhanced_data(session, product_id: int):
    """Get product with enhanced data for variable products"""
    product = session.get(Product, product_id)
    if not product:
        return None

    # Calculate total quantity for variable products
    total_quantity = product.quantity
    variations_data = []

    if product.product_type == ProductType.VARIABLE:
        variations = session.exec(
            select(VariationOption).where(VariationOption.product_id == product_id)
        ).all()

        # Recalculate total quantity from variations
        variation_total_quantity = 0
        for variation in variations:
            variation_total_quantity += variation.quantity
            variations_data.append(variation)

        # Update total quantity
        total_quantity = variation_total_quantity

    # Calculate current stock value
    current_stock_value = None
    if product.purchase_price and product.quantity:
        current_stock_value = product.purchase_price * product.quantity

    # Convert to ProductRead with enhanced data
    product_data = ProductRead.model_validate(product)

    # Add enhanced data
    if hasattr(product_data, "variations"):
        product_data.variations = variations_data

    # Update quantities based on product type
    if product.product_type == ProductType.VARIABLE:
        product_data.total_quantity = total_quantity
        product_data.quantity = total_quantity

    # Add stock value
    product_data.current_stock_value = current_stock_value

    return product_data


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

    # Check if SKU already exists
    if request.sku:
        existing_product = session.exec(
            select(Product).where(Product.sku == request.sku)
        ).first()
        if existing_product:
            return api_response(400, "SKU already exists")

    # Calculate min and max prices and total quantity based on product type
    total_quantity = 0
    min_price = request.min_price or request.price
    max_price = request.max_price or request.price

    if request.product_type == ProductType.SIMPLE:
        min_price = request.price
        max_price = request.price
        total_quantity = request.quantity or 0

    elif request.product_type == ProductType.VARIABLE and request.variations:
        prices = [var.price for var in request.variations]
        min_price = min(prices)
        max_price = max(prices)
        total_quantity = sum(var.quantity for var in request.variations)

    else:
        min_price = request.min_price or request.price
        max_price = request.max_price or request.price
        total_quantity = request.quantity or 0

    # Prepare product data
    product_data = request.model_dump(
        exclude={
            "attributes",
            "variations"
        }
    )
    product_data.update(
        {
            "min_price": min_price,
            "max_price": max_price,
            "quantity": total_quantity,  # Set total quantity
            "attributes": (
                [attr.model_dump() for attr in request.attributes]
                if request.attributes
                else None
            ),
            
        }
    )

    data = Product(**product_data)
    data.slug = uniqueSlugify(session, Product, data.name)
    session.add(data)
    session.commit()
    session.refresh(data)

    # Create variations for variable products
    if request.product_type == ProductType.VARIABLE and request.variations:
        create_variations_for_product(session, data.id, request.variations, data.sku)

    # Return enhanced product data
    enhanced_product = get_product_with_enhanced_data(session, data.id)
    return api_response(200, "Product Created Successfully", enhanced_product)


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

    # Check if SKU already exists
    if request.sku and request.sku != updateData.sku:
        existing_product = session.exec(
            select(Product).where(Product.sku == request.sku)
        ).first()
        if existing_product:
            return api_response(400, "SKU already exists")

    # Calculate total quantity based on product type
    total_quantity = updateData.quantity

    if request.product_type == ProductType.VARIABLE and request.variations:
        total_quantity = sum(var.quantity for var in request.variations)

    elif request.quantity is not None:
        total_quantity = request.quantity

    # Prepare update data
    update_data = request.model_dump(
        exclude_none=True,
        exclude={
            "attributes",
            "variations"
        },
    )

    # Update quantity
    update_data["quantity"] = total_quantity

    if request.attributes is not None:
        update_data["attributes"] = [attr.model_dump() for attr in request.attributes]

    data = updateOp(updateData, ProductUpdate(**update_data), session)

    if data.name:
        data.slug = uniqueSlugify(session, Product, data.name)

    # Update variations for variable products
    if request.product_type == ProductType.VARIABLE and request.variations:
        update_variations_for_product(session, data.id, request.variations, data.sku)
        # Update total quantity after variations are created
        variations = session.exec(
            select(VariationOption).where(VariationOption.product_id == data.id)
        ).all()
        total_variation_quantity = sum(var.quantity for var in variations)
        data.quantity = total_variation_quantity
        session.add(data)

    session.commit()
    session.refresh(data)

    # Return enhanced product data
    enhanced_product = get_product_with_enhanced_data(session, data.id)
    return api_response(200, "Product Updated Successfully", enhanced_product)


@router.get(
    "/read/{id_slug}",
    description="Product ID (int) or slug (str)",
)
def get(id_slug: str, session: GetSession):
    # Check if it's an integer ID
    if id_slug.isdigit():
        product_id = int(id_slug)
        product = session.get(Product, product_id)
    else:
        # Otherwise treat as slug
        product = session.exec(
            select(Product).where(Product.slug.ilike(id_slug))
        ).first()
        product_id = product.id if product else None

    raiseExceptions((product, 404, "Product not found"))

    # Return enhanced product data
    enhanced_product = get_product_with_enhanced_data(session, product_id)
    return api_response(200, "Product Found", enhanced_product)


# ✅ DELETE
@router.delete("/delete/{id}")
def delete(
    id: int,
    session: GetSession,
    user=requirePermission("product-delete"),
):
    product = session.get(Product, id)
    raiseExceptions((product, 404, "Product not found"))

    # Delete variations first
    if product.product_type == ProductType.VARIABLE:
        variations = session.exec(
            select(VariationOption).where(VariationOption.product_id == id)
        ).all()
        for variation in variations:
            session.delete(variation)

    session.delete(product)
    session.commit()
    return api_response(200, f"Product {product.name} deleted")


@router.get("/list", response_model=list[ProductRead])
def list(query_params: ListQueryParams, session: GetSession):
    query_params = vars(query_params)
    searchFields = ["name", "description", "category.name"]
    # return {"msg": "hello"}

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

    # Return enhanced product data
    enhanced_product = get_product_with_enhanced_data(session, id)
    return api_response(200, "Product status updated successfully", enhanced_product)


@router.post("/process-video-url")
def process_video_url(request: dict, session: GetSession):
    """Process video URL and return video data"""
    try:
        url = request.get("url", "")

        if not url:
            return api_response(400, "URL is required")

        if not VideoProcessor.is_supported_video_url(url):
            return api_response(
                400,
                "Unsupported video platform. Supported: YouTube, Vimeo, Dailymotion",
            )

        video_data = VideoProcessor.process_video_url(url)

        if video_data:
            return api_response(200, "Video data extracted successfully", video_data)
        else:
            return api_response(400, "Could not extract video data from the URL")

    except Exception as e:
        print(f"Error processing video URL: {str(e)}")
        return api_response(500, f"Error processing video URL: {str(e)}")


# Sync Variable Product Quantity
@router.post("/{id}/sync-quantity")
def sync_variable_product_quantity(id: int, session: GetSession):
    """Sync variable product quantity with sum of its variations"""
    product = session.get(Product, id)
    raiseExceptions((product, 404, "Product not found"))

    if product.product_type != ProductType.VARIABLE:
        return api_response(400, "Product is not a variable product")

    variations = session.exec(
        select(VariationOption).where(VariationOption.product_id == id)
    ).all()

    total_quantity = sum(var.quantity for var in variations)
    product.quantity = total_quantity
    session.add(product)
    session.commit()

    return api_response(
        200,
        "Quantity synced successfully",
        {
            "product_id": product.id,
            "product_name": product.name,
            "previous_quantity": product.quantity,
            "new_quantity": total_quantity,
            "variations_count": len(variations),
        },
    )


# Product Stock Report
@router.get("/stock-report")
def get_stock_report(
    session: GetSession,
    shop_id: Optional[int] = None,
    low_stock_threshold: int = 10,
    user=requirePermission("product_view", "shop_admin"),
):
    """Get product stock report with purchase and sales data"""
    try:
        # Build base query
        query = select(Product)

        # Filter by user's shops
        shop_ids = [s["id"] for s in user.get("shops", [])]
        if shop_ids:
            query = query.where(Product.shop_id.in_(shop_ids))

        if shop_id:
            if shop_id not in shop_ids:
                return api_response(403, "Access denied to specified shop")
            query = query.where(Product.shop_id == shop_id)

        products = session.exec(query).all()

        stock_report = []
        for product in products:
            # Calculate stock status
            stock_status = "IN_STOCK"
            if product.quantity <= 0:
                stock_status = "OUT_OF_STOCK"
            elif product.quantity <= low_stock_threshold:
                stock_status = "LOW_STOCK"

            # Calculate current stock value
            current_stock_value = (
                product.purchase_price * product.quantity
                if product.purchase_price
                else 0
            )

            stock_report.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "product_type": product.product_type,
                    "current_quantity": product.quantity,
                    "total_purchased": product.total_purchased_quantity,
                    "total_sold": product.total_sold_quantity,
                    "purchase_price": product.purchase_price,
                    "sale_price": product.sale_price or product.price,
                    "current_stock_value": current_stock_value,
                    "stock_status": stock_status,
                    "in_stock": product.in_stock,
                    "last_updated": (
                        product.updated_at.isoformat() if product.updated_at else None
                    ),
                }
            )

        return api_response(
            200, "Stock report generated", stock_report, len(stock_report)
        )

    except Exception as e:
        return api_response(500, f"Error generating stock report: {str(e)}")
