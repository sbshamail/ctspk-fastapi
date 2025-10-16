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
    VariationData,
    GroupedProductItem,
    GroupedProductPricingType,
    GroupedProductConfig,
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


def calculate_grouped_product_price(
    grouped_products: List[GroupedProductItem], config: GroupedProductConfig, session
) -> tuple[float, float, int]:
    """
    Calculate grouped product price, original price, and available quantity
    """
    total_original_price = 0.0
    available_quantity = float("inf")  # Start with infinity, find minimum

    # Calculate original price and find available quantity
    for item in grouped_products:
        product = session.get(Product, item.product_id)
        if product:
            # Get current product price
            current_price = product.sale_price or product.price
            if current_price:
                total_original_price += current_price * item.quantity

            # Determine available quantity based on constituent products
            if not item.is_free:  # Free items don't affect available quantity
                item_available = (
                    product.quantity // item.quantity if item.quantity > 0 else 0
                )
                available_quantity = min(available_quantity, item_available)

    # Calculate final price based on pricing type
    if config.pricing_type == GroupedProductPricingType.FIXED_PRICE:
        final_price = config.fixed_price or total_original_price
    elif config.pricing_type == GroupedProductPricingType.FIXED_DISCOUNT:
        final_price = total_original_price - (config.discount_value or 0)
    elif config.pricing_type == GroupedProductPricingType.PERCENTAGE_DISCOUNT:
        discount = (config.discount_value or 0) / 100
        final_price = total_original_price * (1 - discount)
    elif config.pricing_type == GroupedProductPricingType.FREE_ITEM:
        # For free item, price is sum of paid items only
        paid_items_price = sum(
            (item.product_price or 0) * item.quantity
            for item in grouped_products
            if not item.is_free
        )
        final_price = paid_items_price
    else:
        final_price = total_original_price

    # Ensure final price is not negative
    final_price = max(0, final_price)

    # If no available quantity found (all items are free or no items), set to 0
    if available_quantity == float("inf"):
        available_quantity = 0

    return final_price, total_original_price, int(available_quantity)


def enhance_grouped_products_data(
    session, grouped_products: List[Dict], config: Dict
) -> tuple[List[Dict], float, float, int]:
    """
    Enhance grouped products with current data and calculate pricing
    """
    if not grouped_products:
        return [], 0, 0, 0

    enhanced_items = []
    for item in grouped_products:
        product = session.get(Product, item.get("product_id"))
        if product:
            enhanced_item = {
                "id": item.get("id"),
                "product_id": item.get("product_id"),
                "product_name": product.name,
                "product_sku": product.sku,
                "product_price": product.sale_price or product.price,
                "quantity": item.get("quantity", 1),
                "is_free": item.get("is_free", False),
            }
            enhanced_items.append(enhanced_item)

    # Calculate prices and available quantity
    config_obj = (
        GroupedProductConfig(**config)
        if config
        else GroupedProductConfig(pricing_type=GroupedProductPricingType.FIXED_PRICE)
    )

    final_price, original_price, available_quantity = calculate_grouped_product_price(
        [GroupedProductItem(**item) for item in enhanced_items], config_obj, session
    )

    return enhanced_items, final_price, original_price, available_quantity


def get_product_with_enhanced_data(session, product_id: int):
    """Get product with enhanced data for variable and grouped products"""
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

    # Enhanced grouped products with pricing calculation
    enhanced_grouped_products = []
    final_group_price = product.price
    original_group_price = product.price
    available_quantity = product.quantity

    if product.product_type == ProductType.GROUPED and product.grouped_products:
        enhanced_items, calculated_price, original_price, calculated_quantity = (
            enhance_grouped_products_data(
                session, product.grouped_products, product.grouped_products_config
            )
        )

        enhanced_grouped_products = enhanced_items
        final_group_price = calculated_price
        original_group_price = original_price
        available_quantity = calculated_quantity

    # Calculate current stock value
    current_stock_value = None
    if product.purchase_price and product.quantity:
        current_stock_value = product.purchase_price * product.quantity

    # Convert to ProductRead with enhanced data
    product_data = ProductRead.model_validate(product)

    # Add enhanced data
    if hasattr(product_data, "variations"):
        product_data.variations = variations_data

    if hasattr(product_data, "grouped_products"):
        product_data.grouped_products = enhanced_grouped_products

    # Update quantities and prices based on product type
    if product.product_type == ProductType.VARIABLE:
        product_data.total_quantity = total_quantity
        product_data.quantity = (
            total_quantity  # Update main quantity with sum of variations
        )

    elif product.product_type == ProductType.GROUPED:
        product_data.price = final_group_price
        product_data.min_price = final_group_price
        product_data.max_price = final_group_price
        product_data.quantity = available_quantity
        product_data.grouped_products_config = (
            GroupedProductConfig(**product.grouped_products_config)
            if product.grouped_products_config
            else None
        )

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

    # Validate SKU format if provided
    if request.sku and not request.sku.startswith("SK-"):
        return api_response(400, "SKU must start with 'SK-' prefix")

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

    elif request.product_type == ProductType.GROUPED and request.grouped_products:
        # Calculate grouped product pricing and availability
        enhanced_items, final_price, original_price, available_quantity = (
            enhance_grouped_products_data(
                session,
                [item.model_dump() for item in request.grouped_products],
                (
                    request.grouped_products_config.model_dump()
                    if request.grouped_products_config
                    else None
                ),
            )
        )

        min_price = final_price
        max_price = final_price
        total_quantity = available_quantity

        # Store enhanced grouped products data
        grouped_products_data = enhanced_items
        grouped_config_data = (
            request.grouped_products_config.model_dump()
            if request.grouped_products_config
            else None
        )
    else:
        min_price = request.min_price or request.price
        max_price = request.max_price or request.price
        total_quantity = request.quantity or 0
        grouped_products_data = (
            [item.model_dump() for item in request.grouped_products]
            if request.grouped_products
            else None
        )
        grouped_config_data = (
            request.grouped_products_config.model_dump()
            if request.grouped_products_config
            else None
        )

    # Prepare product data
    product_data = request.model_dump(
        exclude={
            "attributes",
            "variations",
            "grouped_products",
            "grouped_products_config",
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
            "grouped_products": grouped_products_data,
            "grouped_products_config": grouped_config_data,
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

    # Validate SKU if provided
    if request.sku and not request.sku.startswith("SK-"):
        return api_response(400, "SKU must start with 'SK-' prefix")

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

    elif request.product_type == ProductType.GROUPED and request.grouped_products:
        # Calculate grouped product pricing and availability
        enhanced_items, final_price, original_price, calculated_quantity = (
            enhance_grouped_products_data(
                session,
                [item.model_dump() for item in request.grouped_products],
                (
                    request.grouped_products_config.model_dump()
                    if request.grouped_products_config
                    else None
                ),
            )
        )

        total_quantity = calculated_quantity

        # Update prices for grouped product
        if "min_price" not in request.model_dump(exclude_none=True):
            request.min_price = final_price
        if "max_price" not in request.model_dump(exclude_none=True):
            request.max_price = final_price
        if "price" not in request.model_dump(exclude_none=True):
            request.price = final_price

    elif request.quantity is not None:
        total_quantity = request.quantity

    # Prepare update data
    update_data = request.model_dump(
        exclude_none=True,
        exclude={
            "attributes",
            "variations",
            "grouped_products",
            "grouped_products_config",
        },
    )

    # Update quantity
    update_data["quantity"] = total_quantity

    if request.attributes is not None:
        update_data["attributes"] = [attr.model_dump() for attr in request.attributes]

    if request.grouped_products is not None:
        # Use enhanced data for grouped products
        if request.product_type == ProductType.GROUPED:
            enhanced_items, _, _, _ = enhance_grouped_products_data(
                session,
                [item.model_dump() for item in request.grouped_products],
                (
                    request.grouped_products_config.model_dump()
                    if request.grouped_products_config
                    else None
                ),
            )
            update_data["grouped_products"] = enhanced_items
        else:
            update_data["grouped_products"] = [
                item.model_dump() for item in request.grouped_products
            ]

    if request.grouped_products_config is not None:
        update_data["grouped_products_config"] = (
            request.grouped_products_config.model_dump()
        )

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


# Group Product Availability Check
@router.get("/{id}/group-availability")
def get_group_availability(id: int, session: GetSession):
    """Get real-time availability of grouped product"""
    product = session.get(Product, id)
    raiseExceptions((product, 404, "Product not found"))

    if product.product_type != ProductType.GROUPED:
        return api_response(400, "Product is not a grouped product")

    if not product.grouped_products:
        return api_response(
            200,
            "Group availability",
            {
                "available": False,
                "message": "No products in group",
                "constituent_products": [],
            },
        )

    constituent_status = []
    can_sell = True
    limiting_products = []

    for item in product.grouped_products:
        constituent = session.get(Product, item.get("product_id"))
        if constituent:
            required_qty = item.get("quantity", 1)
            available_qty = constituent.quantity
            is_available = available_qty >= required_qty
            is_free = item.get("is_free", False)

            constituent_status.append(
                {
                    "product_id": constituent.id,
                    "product_name": constituent.name,
                    "required_quantity": required_qty,
                    "available_quantity": available_qty,
                    "is_available": is_available,
                    "is_free": is_free,
                }
            )

            if not is_available and not is_free:
                can_sell = False
                limiting_products.append(constituent.name)

    message = (
        "Available for purchase"
        if can_sell
        else f"Insufficient stock for: {', '.join(limiting_products)}"
    )

    return api_response(
        200,
        "Group availability",
        {
            "available": can_sell,
            "message": message,
            "constituent_products": constituent_status,
            "total_available_quantity": product.quantity,
        },
    )


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
