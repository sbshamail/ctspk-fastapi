from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import select, func, and_, or_, cast, Float, exists
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
)
from src.api.models.manufacturer_model.manufacturerModel import Manufacturer
from src.api.models.shop_model.shopsModel import Shop
from pydantic import BaseModel, field_validator
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requirePermission,
    requireSignin,
)
from src.api.core.sku_generator import generate_unique_sku, generate_sku_for_variation
from sqlalchemy.orm import aliased
from src.api.core.transaction_logger import TransactionLogger

router = APIRouter(prefix="/product", tags=["Product"])


def distinct_products(products):
    """Remove duplicate products by ID, preserving order."""
    seen = set()
    result = []
    for p in products:
        if p.id not in seen:
            seen.add(p.id)
            result.append(p)
    return result


# Pydantic schemas for new routes
class UpdateQtyPriceRequest(BaseModel):
    quantity: Optional[int] = None
    price: Optional[float] = None
    sale_price: Optional[float] = None
    purchase_price: Optional[float] = None
    notes: str
    variation_option_id: Optional[int] = None

    @field_validator('quantity')
    def validate_quantity(cls, v, info):
        if v is not None and v < 0:
            raise ValueError('Quantity cannot be negative')
        return v

    @field_validator('sale_price')
    def validate_sale_price(cls, v, info):
        # Get price from the data being validated
        price = info.data.get('price')
        if v is not None and v > 0 and price is not None and v >= price:
            raise ValueError('Sale price must be less than price')
        return v


class RemoveQtyRequest(BaseModel):
    quantity: int
    notes: str
    variation_option_id: Optional[int] = None

    @field_validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v


def apply_number_range_filter(query, query_params_dict, Model):
    """Helper function to apply numberRange filter to a query"""
    if query_params_dict.get('numberRange'):
        try:
            import json
            import ast
            number_range = query_params_dict['numberRange']
            try:
                parsed = json.loads(number_range)
            except json.JSONDecodeError:
                parsed = ast.literal_eval(number_range)

            column_name = parsed[0]
            min_val = float(parsed[1]) if len(parsed) > 1 and parsed[1] is not None else None
            max_val = float(parsed[2]) if len(parsed) > 2 and parsed[2] is not None else None

            if hasattr(Model, column_name):
                column = getattr(Model, column_name)
                if min_val is not None and max_val is not None:
                    query = query.where(column.between(min_val, max_val))
                elif min_val is not None:
                    query = query.where(column >= min_val)
                elif max_val is not None:
                    query = query.where(column <= max_val)
        except Exception as e:
            print(f"Error parsing numberRange: {e}")
    return query


def apply_sort_filter(query, query_params_dict, Model, default_sort_field=None, default_sort_order="desc"):
    """Helper function to apply sort filter to a query"""
    if query_params_dict.get('sort'):
        try:
            import json
            import ast
            sort_param = query_params_dict['sort']
            try:
                parsed = json.loads(sort_param)
            except json.JSONDecodeError:
                parsed = ast.literal_eval(sort_param)

            column_name, direction = parsed[0], parsed[1]

            if hasattr(Model, column_name):
                column = getattr(Model, column_name)
                if direction.lower() == "asc":
                    query = query.order_by(column.asc())
                else:
                    query = query.order_by(column.desc())
        except Exception as e:
            print(f"Error parsing sort: {e}")
            # Apply default sort if parsing fails
            if default_sort_field and hasattr(Model, default_sort_field):
                column = getattr(Model, default_sort_field)
                if default_sort_order.lower() == "asc":
                    query = query.order_by(column.asc())
                else:
                    query = query.order_by(column.desc())
    elif default_sort_field and hasattr(Model, default_sort_field):
        # Apply default sort if no sort param provided
        column = getattr(Model, default_sort_field)
        if default_sort_order.lower() == "asc":
            query = query.order_by(column.asc())
        else:
            query = query.order_by(column.desc())
    return query


def get_unique_enhanced_products(session, products, return_dict=False):
    """
    Remove duplicate products by ID and return enhanced product data.
    Maintains the original ordering while ensuring each product appears only once.

    Args:
        session: Database session
        products: List of Product objects or product IDs
        return_dict: If True, returns list of dicts, otherwise returns list of ProductRead objects

    Returns:
        List of unique enhanced products (either as ProductRead objects or dicts)
    """
    seen_ids = set()
    enhanced_products = []

    for product in products:
        # Get product ID (handle both Product objects and raw IDs)
        product_id = product.id if hasattr(product, 'id') else product

        # Skip if we've already seen this product
        if product_id in seen_ids:
            continue

        seen_ids.add(product_id)

        # Get enhanced product data
        enhanced_product = get_product_with_enhanced_data(session, product_id)
        if enhanced_product:
            if return_dict:
                enhanced_products.append(enhanced_product.model_dump())
            else:
                enhanced_products.append(enhanced_product)

    return enhanced_products


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


# def get_product_with_enhanced_data(session, product_id: int):
#     """Get product with enhanced data for variable products"""
#     product = session.get(Product, product_id)
#     if not product:
#         return None

#     # Calculate total quantity for variable products
#     total_quantity = product.quantity
#     variations_data = []

#     if product.product_type == ProductType.VARIABLE:
#         variations = session.exec(
#             select(VariationOption).where(VariationOption.product_id == product_id)
#         ).all()

#         # Recalculate total quantity from variations
#         variation_total_quantity = 0
#         for variation in variations:
#             variation_total_quantity += variation.quantity
#             variations_data.append(variation)

#         # Update total quantity
#         total_quantity = variation_total_quantity

#     # Calculate current stock value
#     current_stock_value = None
#     if product.purchase_price and product.quantity:
#         current_stock_value = product.purchase_price * product.quantity

#     # Convert to ProductRead with enhanced data
#     product_data = ProductRead.model_validate(product)

#     # Add enhanced data
#     if hasattr(product_data, "variations"):
#         product_data.variations = variations_data

#     # Update quantities based on product type
#     if product.product_type == ProductType.VARIABLE:
#         product_data.total_quantity = total_quantity
#         product_data.quantity = total_quantity

#     # Add stock value
#     product_data.current_stock_value = current_stock_value

#     return product_data

def get_product_with_enhanced_data(session, product_id: int):
    """Get product with enhanced data for variable products"""
    product = session.get(Product, product_id)
    if not product:
        return None

    # Calculate total quantity for variable products
    total_quantity = product.quantity
    variations_data = []
    variations_count = 0

    if product.product_type == ProductType.VARIABLE:
        variations = session.exec(
            select(VariationOption).where(VariationOption.product_id == product_id)
        ).all()

        # Recalculate total quantity from variations
        variation_total_quantity = 0
        for variation in variations:
            variation_total_quantity += variation.quantity
            variations_data.append(variation)

        # Update total quantity and count
        total_quantity = variation_total_quantity
        variations_count = len(variations)

    # Calculate current stock value
    current_stock_value = None
    if product.purchase_price and product.quantity:
        current_stock_value = product.purchase_price * product.quantity

    # Convert to ProductRead with enhanced data
    product_data = ProductRead.model_validate(product)
    
    # Set the calculated values
    product_data.total_quantity = total_quantity
    product_data.variations_count = variations_count
    product_data.current_stock_value = current_stock_value

    return product_data

# ✅ CREATE
@router.post("/create")
@handle_async_wrapper
def create(
    request: ProductCreate,
    session: GetSession,
    user=requirePermission(["product:create", "vendor-product:create"]),
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
    product_data = request.model_dump(exclude={"attributes", "variations"})
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
    logger = TransactionLogger(session)
    logger.log_product_creation(
        product=data,
        user_id=user["id"],
        notes=f"Product created via API: {data.name}"
    )
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
    user=requirePermission(["product:update", "vendor-product:update"]),
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
        exclude={"attributes", "variations"},
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
    user=requirePermission(["product:delete","vendor-product:delete"]),
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
def list(
    query_params: ListQueryParams,
    session: GetSession,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_feature: Optional[bool] = Query(None, description="Filter by feature status"),
):
    query_params = vars(query_params)
    searchFields = ["name", "description", "category.name"]

    # Add filters to customFilters if provided
    custom_filters = []
    if is_active is not None:
        custom_filters.append(["is_active", is_active])
    if is_feature is not None:
        custom_filters.append(["is_feature", is_feature])
    if custom_filters:
        query_params["customFilters"] = custom_filters

    # Filter out products from inactive/disapproved shops
    def active_shop_filter(statement, Model):
        return statement.join(Shop, Model.shop_id == Shop.id).where(Shop.is_active == True)

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
        otherFilters=active_shop_filter,
    )


@router.get("/my-products")
def my_products(
    query_params: ListQueryParams,
    session: GetSession,
    user: requireSignin,
    shop_id: Optional[int] = None,
):
    """
    Get products for the authenticated user's shops.
    Filters products by the user's associated shops.
    Supports all standard list filters (searchTerm, columnFilters, etc.)
    Optional shop_id parameter to filter by a specific shop.
    """
    # Get shop IDs from user
    shop_ids = [s["id"] for s in user.get("shops", [])]

    if not shop_ids:
        return api_response(200, "No shops found for user", [], 0)

    # If specific shop_id provided, validate it belongs to user
    if shop_id:
        if shop_id not in shop_ids:
            return api_response(403, "Access denied to specified shop")
        shop_ids = [shop_id]

    query_params_dict = vars(query_params)
    searchFields = ["name", "description", "category.name"]

    # Create filter function for user's shops
    def shop_filter(statement, Model):
        return statement.where(Model.shop_id.in_(shop_ids))

    return listRecords(
        query_params=query_params_dict,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
        otherFilters=shop_filter,
    )


@router.get("/products/related/{category_id}")
def get_products_by_category(
    category_id: int,
    session: GetSession,
    query_params: ListQueryParams,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_feature: Optional[bool] = Query(None, description="Filter by feature status"),
):
    # Validate that category exists
    category = session.get(Category, category_id)
    if not category:
        return api_response(404, f"Category with id {category_id} not found", [], 0)

    # Get all descendant category IDs in a single query (max 3 levels)
    # Level 1: direct children, Level 2: grandchildren
    descendants = session.exec(
        select(Category.id).where(
            or_(
                Category.parent_id == category_id,  # Direct children
                Category.parent_id.in_(
                    select(Category.id).where(Category.parent_id == category_id)
                )  # Grandchildren
            )
        )
    ).all()

    category_ids = [category_id] + [d for d in descendants]

    # Convert query_params to dict
    query_params = vars(query_params)
    searchFields = ["name", "description", "category.name"]

    # Add is_active and is_feature to customFilters if provided
    custom_filters = []
    if is_active is not None:
        custom_filters.append(["is_active", is_active])
    if is_feature is not None:
        custom_filters.append(["is_feature", is_feature])
    if custom_filters:
        query_params["customFilters"] = custom_filters

    # Filter by category_ids and exclude products from inactive/disapproved shops
    def category_and_shop_filter(statement, Model):
        return (
            statement
            .join(Shop, Model.shop_id == Shop.id)
            .where(Shop.is_active == True)
            .where(Model.category_id.in_(category_ids))
        )

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
        otherFilters=category_and_shop_filter,
    )


# ✅ PATCH Product status
@router.patch("/{id}/status")
def patch_product_status(
    id: int,
    request: ProductActivate,
    session: GetSession,
    user=requirePermission(["product:update*", "vendor-product:update"]),
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

    except HTTPException:
        raise
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


@router.get("/trending")
def get_trending_products(
    session: GetSession,
    query_params: ListQueryParams,
    is_active: bool = True,
    shop_id: Optional[int] = None,  # Filter by shop
    days: int = 30  # Trending in last X days
):
    """
    Get trending products based on sales in recent days with advanced filtering
    """
    try:
        # Extract query params
        query_params_dict = vars(query_params)
        limit = query_params_dict.get('limit', 10)
        page = query_params_dict.get('page', 1)
        skip = (page - 1) * limit

        # Calculate date threshold
        from datetime import datetime, timedelta
        threshold_date = datetime.now() - timedelta(days=days)

        # Query products with highest sales in recent period
        # Using total_sold_quantity as a proxy for trending
        query = (
            select(Product)
            .where(
                and_(
                    Product.is_active == is_active,
                    Product.total_sold_quantity > 0,
                    Product.created_at >= threshold_date
                )
            )
        )

        # Add shop filter
        if shop_id:
            query = query.where(Product.shop_id == shop_id)

        # Apply searchTerm
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            query = query.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        # Apply columnFilters
        if query_params_dict.get('columnFilters'):
            import ast
            column_filters = ast.literal_eval(query_params_dict['columnFilters'])
            for col_filter in column_filters:
                field_name, field_value = col_filter[0], col_filter[1]
                if hasattr(Product, field_name):
                    field = getattr(Product, field_name)
                    if isinstance(field_value, list):
                        query = query.where(field.in_(field_value))
                    else:
                        query = query.where(field == field_value)

        # Apply numberRange filter
        query = apply_number_range_filter(query, query_params_dict, Product)

        # Apply sort filter
        query = apply_sort_filter(query, query_params_dict, Product, "total_sold_quantity", "desc")

        query = (
            query
            .offset(skip)
            .limit(limit)
        )

        products = distinct_products(session.exec(query).all())

        # Remove duplicates by product id
        seen_ids = set()
        enhanced_products = []
        for product in products:
            if product.id in seen_ids:
                continue
            seen_ids.add(product.id)
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            if enhanced_product:
                enhanced_products.append(enhanced_product)

        # Check if no products found
        if not enhanced_products:
            return api_response(
                404,
                "No trending products found",
                [],
                0
            )

        return api_response(
            200,
            f"Found {len(enhanced_products)} trending products",
            enhanced_products,
            len(enhanced_products)
        )

    except Exception as e:
        return api_response(500, f"Error fetching trending products: {str(e)}")

@router.get("/limited-edition")
def get_limited_edition_products(
    session: GetSession,
    query_params: ListQueryParams,
    is_active: bool = True,
    shop_id: Optional[int] = None,  # Filter by shop
    low_stock_threshold: int = 20
):
    """
    Get limited edition products (low stock items) with advanced filtering
    """
    try:
        # Extract query params
        query_params_dict = vars(query_params)
        limit = query_params_dict.get('limit', 10)
        page = query_params_dict.get('page', 1)
        skip = (page - 1) * limit

        query = (
            select(Product)
            .join(Shop, Product.shop_id == Shop.id)
            .where(
                and_(
                    Product.is_active == is_active,
                    Product.quantity > 0,
                    Product.quantity <= low_stock_threshold,
                    Shop.is_active == True
                )
            )
        )

        # Add shop filter
        if shop_id:
            query = query.where(Product.shop_id == shop_id)

        # Apply searchTerm
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            query = query.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        # Apply columnFilters
        if query_params_dict.get('columnFilters'):
            import ast
            column_filters = ast.literal_eval(query_params_dict['columnFilters'])
            for col_filter in column_filters:
                field_name, field_value = col_filter[0], col_filter[1]
                if hasattr(Product, field_name):
                    field = getattr(Product, field_name)
                    if isinstance(field_value, list):
                        query = query.where(field.in_(field_value))
                    else:
                        query = query.where(field == field_value)

        # Apply numberRange filter
        query = apply_number_range_filter(query, query_params_dict, Product)

        # Apply sort filter
        query = apply_sort_filter(query, query_params_dict, Product, "quantity", "asc")

        query = (
            query
            .offset(skip)
            .limit(limit)
        )

        products = distinct_products(session.exec(query).all())

        # Get unique enhanced products
        enhanced_products = get_unique_enhanced_products(session, products)

        # Check if no products found
        if not enhanced_products:
            return api_response(
                404,
                "No limited edition products found",
                [],
                0
            )

        return api_response(
            200,
            f"Found {len(enhanced_products)} limited edition products",
            enhanced_products,
            len(enhanced_products)
        )

    except Exception as e:
        return api_response(500, f"Error fetching limited edition products: {str(e)}")

@router.get("/best-sellers")
def get_best_seller_products(
    session: GetSession,
    query_params: ListQueryParams,
    is_active: bool = True,
    shop_id: Optional[int] = None,  # Filter by shop
    days: Optional[int] = None  # Optional: best sellers in specific period
):
    """
    Get best seller products based on total sold quantity with advanced filtering
    """
    try:
        # Extract query params
        query_params_dict = vars(query_params)
        limit = query_params_dict.get('limit', 10)
        page = query_params_dict.get('page', 1)
        skip = (page - 1) * limit

        query = (
            select(Product)
            .join(Shop, Product.shop_id == Shop.id)
            .where(
                and_(
                    Product.is_active == is_active,
                    Shop.is_active == True
                )
            )
        )

        # Add shop filter
        if shop_id:
            query = query.where(Product.shop_id == shop_id)

        # If days parameter provided, filter by date
        if days:
            from datetime import datetime, timedelta
            threshold_date = datetime.now() - timedelta(days=days)
            query = query.where(Product.created_at >= threshold_date)

        # Apply searchTerm
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            query = query.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        # Apply columnFilters
        if query_params_dict.get('columnFilters'):
            import ast
            column_filters = ast.literal_eval(query_params_dict['columnFilters'])
            for col_filter in column_filters:
                field_name, field_value = col_filter[0], col_filter[1]
                if hasattr(Product, field_name):
                    field = getattr(Product, field_name)
                    if isinstance(field_value, list):
                        query = query.where(field.in_(field_value))
                    else:
                        query = query.where(field == field_value)

        # Apply numberRange filter
        query = apply_number_range_filter(query, query_params_dict, Product)

        query = query.where(Product.total_sold_quantity > 0)

        # Apply sort filter
        query = apply_sort_filter(query, query_params_dict, Product, "total_sold_quantity", "desc")

        query = (
            query
            .offset(skip)
            .limit(limit)
        )

        products = distinct_products(session.exec(query).all())

        # Get unique enhanced products
        enhanced_products = get_unique_enhanced_products(session, products)

        # Check if no products found
        if not enhanced_products:
            return api_response(
                404,
                "No best seller products found",
                [],
                0
            )

        return api_response(
            200,
            f"Found {len(enhanced_products)} best seller products",
            enhanced_products,
            len(enhanced_products)
        )

    except Exception as e:
        return api_response(500, f"Error fetching best seller products: {str(e)}")

# NEW: Enhanced stock report with filtering options
@router.get("/stock-report")
def get_stock_report(
    session: GetSession,
    shop_id: Optional[int] = None,
    low_stock_threshold: int = 10,
    is_active: Optional[bool] = None,  # NEW: Filter by active status
    order_by: Optional[str] = None,    # NEW: Order by field
    user=requirePermission(["product:view", "vendor-product:view"]),
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
            
        # NEW: Filter by is_active status
        if is_active is not None:
            query = query.where(Product.is_active == is_active)

        # NEW: Add ordering
        if order_by:
            if order_by.startswith('-'):
                # Descending order
                field = getattr(Product, order_by[1:], None)
                if field:
                    query = query.order_by(field.desc())
            else:
                # Ascending order
                field = getattr(Product, order_by, None)
                if field:
                    query = query.order_by(field.asc())

        products = distinct_products(session.exec(query).all())

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
                    "is_active": product.is_active,  # NEW: Include active status
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
    
    # Add this new route in productRoute.py

@router.get("/sales")
def get_sale_products(
    session: GetSession,
    query_params: ListQueryParams,
    is_active: bool = True,  # Filter by active status
    shop_id: Optional[int] = None,  # Filter by shop
    user=requirePermission(["product:view", "vendor-product:view"]),
):
    """
    Get products that are on sale with advanced filtering
    - For simple products: sale_price > 0 and sale_price < price
    - For variable products: variation options with sale_price > 0 and sale_price < price
    - Includes is_active filter
    """
    try:
        # Extract query params
        query_params_dict = vars(query_params)
        limit = query_params_dict.get('limit', 50)
        page = query_params_dict.get('page', 1)
        skip = (page - 1) * limit

        # Build base query for simple products on sale
        simple_products_query = (
            select(Product)
            .join(Shop, Product.shop_id == Shop.id)
            .where(
                and_(
                    Product.is_active == is_active,
                    Shop.is_active == True,
                    Product.product_type == ProductType.SIMPLE,
                    Product.sale_price > 0,
                    Product.sale_price < Product.price,
                    Product.price > 0  # Ensure price is valid
                )
            )
        )

        # Filter by shop_id parameter or user's shops
        if shop_id:
            simple_products_query = simple_products_query.where(Product.shop_id == shop_id)
        else:
            shop_ids = [s["id"] for s in user.get("shops", [])]
            if shop_ids:
                simple_products_query = simple_products_query.where(Product.shop_id.in_(shop_ids))

        # Apply searchTerm
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            simple_products_query = simple_products_query.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        # Get simple products on sale
        simple_products = distinct_products(session.exec(
            simple_products_query
            .offset(skip)
            .limit(limit)
        ).all())

        # Query for variable products that have variations on sale
        variable_products_query = (
            select(Product)
            .join(Shop, Product.shop_id == Shop.id)
            .join(VariationOption, Product.id == VariationOption.product_id)
            .where(
                and_(
                    Product.is_active == is_active,
                    Shop.is_active == True,
                    Product.product_type == ProductType.VARIABLE,
                    VariationOption.sale_price.isnot(None),
                    VariationOption.sale_price != "",
                    cast(VariationOption.sale_price, Float) > 0,
                    cast(VariationOption.sale_price, Float) < cast(VariationOption.price, Float),
                    cast(VariationOption.price, Float) > 0
                )
            )
            .distinct(Product.id)  # Avoid duplicate products
        )

        # Filter by shop_id parameter or user's shops
        if shop_id:
            variable_products_query = variable_products_query.where(Product.shop_id == shop_id)
        else:
            shop_ids = [s["id"] for s in user.get("shops", [])]
            if shop_ids:
                variable_products_query = variable_products_query.where(Product.shop_id.in_(shop_ids))

        # Apply searchTerm for variable products
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            variable_products_query = variable_products_query.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        # Get variable products with sale variations
        variable_products = distinct_products(session.exec(
            variable_products_query
            .offset(skip)
            .limit(limit)
        ).all())

        # Combine and deduplicate products
        all_products = simple_products + variable_products

        # Get unique enhanced products (maintain order and remove duplicates)
        seen_ids = set()
        sale_products = []
        for product in all_products:
            if product.id not in seen_ids:
                seen_ids.add(product.id)
                sale_products.append(product)
                if len(sale_products) >= limit:
                    break

        # Enhance product data with sale-specific information
        enhanced_products = []
        for product in sale_products:
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            if enhanced_product:
                # Add sale-specific information
                product_dict = enhanced_product.model_dump()
                
                # Calculate discount percentage for simple products
                if product.product_type == ProductType.SIMPLE:
                    if product.price and product.sale_price:
                        discount_percent = ((product.price - product.sale_price) / product.price) * 100
                        product_dict['discount_percent'] = round(discount_percent, 2)
                    else:
                        product_dict['discount_percent'] = 0
                
                # For variable products, find which variations are on sale
                elif product.product_type == ProductType.VARIABLE:
                    sale_variations = session.exec(
                        select(VariationOption)
                        .where(
                            and_(
                                VariationOption.product_id == product.id,
                                VariationOption.sale_price.isnot(None),
                                VariationOption.sale_price != "",
                                cast(VariationOption.sale_price, Float) > 0,
                                cast(VariationOption.sale_price, Float) < cast(VariationOption.price, Float)
                            )
                        )
                    ).all()
                    
                    product_dict['sale_variations_count'] = len(sale_variations)
                    
                    # Calculate average discount for variable products
                    if sale_variations:
                        total_discount = 0
                        for var in sale_variations:
                            try:
                                price_val = float(var.price)
                                sale_price_val = float(var.sale_price) if var.sale_price else price_val
                                if price_val > 0:
                                    discount = ((price_val - sale_price_val) / price_val) * 100
                                    total_discount += discount
                            except (ValueError, TypeError):
                                continue
                        
                        if total_discount > 0:
                            product_dict['average_discount_percent'] = round(total_discount / len(sale_variations), 2)
                        else:
                            product_dict['average_discount_percent'] = 0
                    else:
                        product_dict['average_discount_percent'] = 0
                
                enhanced_products.append(product_dict)

        # Check if no products found
        if not enhanced_products:
            return api_response(
                404,
                "No sale products found",
                [],
                0
            )

        return api_response(
            200,
            f"Found {len(enhanced_products)} sale products",
            enhanced_products,
            len(enhanced_products)
        )

    except Exception as e:
        print(f"Error fetching sale products: {str(e)}")
        return api_response(500, f"Error fetching sale products: {str(e)}")


# Alternative version with better performance using subqueries
@router.get("/sales-optimized")
def get_sale_products_optimized(
    session: GetSession,
    query_params: ListQueryParams,
    is_active: bool = True,
    shop_id: Optional[int] = None,  # Filter by shop
    product_type: Optional[str] = None,  # Optional filter by product type
    user=requirePermission(["product:view", "vendor-product:view"]),
):
    """
    Optimized version of sale products query with advanced filtering
    """
    try:
        # Extract query params
        query_params_dict = vars(query_params)
        limit = query_params_dict.get('limit', 50)
        page = query_params_dict.get('page', 1)
        skip = (page - 1) * limit

        # Build the main query
        query = select(Product).where(Product.is_active == is_active)

        # Filter by shop_id parameter or user's shops
        if shop_id:
            query = query.where(Product.shop_id == shop_id)
        else:
            shop_ids = [s["id"] for s in user.get("shops", [])]
            if shop_ids:
                query = query.where(Product.shop_id.in_(shop_ids))

        # Filter by product type if specified
        if product_type:
            if product_type.upper() == "SIMPLE":
                query = query.where(Product.product_type == ProductType.SIMPLE)
            elif product_type.upper() == "VARIABLE":
                query = query.where(Product.product_type == ProductType.VARIABLE)
        
        # Subquery for simple products on sale
        simple_sale_condition = and_(
            Product.product_type == ProductType.SIMPLE,
            Product.sale_price > 0,
            Product.sale_price < Product.price
        )
        
        # Subquery for variable products with sale variations
        variable_sale_condition = and_(
            Product.product_type == ProductType.VARIABLE,
            exists().where(
                and_(
                    VariationOption.product_id == Product.id,
                    VariationOption.sale_price.isnot(None),
                    VariationOption.sale_price != "",
                    cast(VariationOption.sale_price, Float) > 0,
                    cast(VariationOption.sale_price, Float) < cast(VariationOption.price, Float)
                )
            )
        )
        
        # Combine conditions
        query = query.where(or_(simple_sale_condition, variable_sale_condition))

        # Apply searchTerm
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            query = query.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        # Apply columnFilters
        if query_params_dict.get('columnFilters'):
            import ast
            column_filters = ast.literal_eval(query_params_dict['columnFilters'])
            for col_filter in column_filters:
                field_name, field_value = col_filter[0], col_filter[1]
                if hasattr(Product, field_name):
                    field = getattr(Product, field_name)
                    if isinstance(field_value, list):
                        query = query.where(field.in_(field_value))
                    else:
                        query = query.where(field == field_value)

        # Add ordering by discount amount (highest discount first)
        from sqlalchemy import case
        
        discount_case = case(
            (Product.product_type == ProductType.SIMPLE, 
             (Product.price - Product.sale_price) / Product.price * 100),
            else_=0
        ).label('discount_percent')
        
        query = query.order_by(discount_case.desc())
        
        # Execute query
        products = distinct_products(session.exec(
            query
            .offset(skip)
            .limit(limit)
        ).all())

        # Enhance product data
        enhanced_products = []
        for product in products:
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            if enhanced_product:
                product_data = enhanced_product.model_dump()
                
                # Add sale information
                if product.product_type == ProductType.SIMPLE:
                    discount = ((product.price - product.sale_price) / product.price) * 100
                    product_data['discount_percent'] = round(discount, 2)
                    product_data['sale_variations_count'] = 0
                    
                elif product.product_type == ProductType.VARIABLE:
                    # Count sale variations
                    sale_vars = session.exec(
                        select(VariationOption)
                        .where(
                            and_(
                                VariationOption.product_id == product.id,
                                VariationOption.sale_price.isnot(None),
                                cast(VariationOption.sale_price, Float) > 0,
                                cast(VariationOption.sale_price, Float) < cast(VariationOption.price, Float)
                            )
                        )
                    ).all()
                    
                    product_data['sale_variations_count'] = len(sale_vars)
                    
                    # Calculate max discount
                    max_discount = 0
                    for var in sale_vars:
                        try:
                            price_val = float(var.price)
                            sale_val = float(var.sale_price)
                            discount = ((price_val - sale_val) / price_val) * 100
                            max_discount = max(max_discount, discount)
                        except (ValueError, TypeError):
                            continue
                    
                    product_data['max_discount_percent'] = round(max_discount, 2)
                
                enhanced_products.append(product_data)
        
        # Get total count for pagination
        count_query = select(func.count(Product.id)).where(
            and_(
                Product.is_active == is_active,
                or_(simple_sale_condition, variable_sale_condition)
            )
        )
        if shop_ids:
            count_query = count_query.where(Product.shop_id.in_(shop_ids))

        total_count = session.exec(count_query).first()

        # Check if no products found
        if not enhanced_products:
            return api_response(
                404,
                "No sale products found",
                [],
                0
            )

        return api_response(
            200,
            f"Found {len(enhanced_products)} sale products",
            enhanced_products,
            total_count
        )

    except Exception as e:
        print(f"Error in optimized sale products: {str(e)}")
        return api_response(500, f"Error fetching sale products: {str(e)}")


# Simple version for public access (without shop filtering)
@router.get("/sales/public")
def get_public_sale_products(
    session: GetSession,
    query_params: ListQueryParams,
    is_active: bool = True,
    shop_id: Optional[int] = None
):
    """
    Public endpoint for sale products (no authentication required)
    """
    try:
        # Extract query params
        query_params_dict = vars(query_params)
        limit = query_params_dict.get('limit', 20)
        page = query_params_dict.get('page', 1)
        skip = (page - 1) * limit

        # Simple products on sale
        simple_query = select(Product).where(
            and_(
                Product.is_active == is_active,
                Product.product_type == ProductType.SIMPLE,
                Product.sale_price > 0,
                Product.sale_price < Product.price
            )
        )

        # Add shop filter if provided
        if shop_id:
            simple_query = simple_query.where(Product.shop_id == shop_id)

        # Apply searchTerm
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            simple_query = simple_query.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        simple_products = distinct_products(session.exec(
            simple_query
            .offset(skip)
            .limit(limit)
        ).all())

        # Variable products with sale variations
        variable_query = (
            select(Product)
            .join(VariationOption, Product.id == VariationOption.product_id)
            .where(
                and_(
                    Product.is_active == is_active,
                    Product.product_type == ProductType.VARIABLE,
                    VariationOption.sale_price.isnot(None),
                    cast(VariationOption.sale_price, Float) > 0,
                    cast(VariationOption.sale_price, Float) < cast(VariationOption.price, Float)
                )
            )
            .distinct(Product.id)
        )

        # Add shop filter if provided
        if shop_id:
            variable_query = variable_query.where(Product.shop_id == shop_id)

        # Apply searchTerm
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            variable_query = variable_query.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        variable_products = distinct_products(session.exec(
            variable_query
            .offset(skip)
            .limit(limit)
        ).all())

        # Combine results and get unique enhanced products
        all_products = simple_products + variable_products

        # Get unique products maintaining order and limiting to requested amount
        seen_ids = set()
        unique_product_list = []
        for product in all_products:
            if product.id not in seen_ids:
                seen_ids.add(product.id)
                unique_product_list.append(product)
                if len(unique_product_list) >= limit:
                    break

        # Enhance data
        enhanced_products = get_unique_enhanced_products(session, unique_product_list, return_dict=True)

        # Check if no products found
        if not enhanced_products:
            return api_response(
                404,
                "No sale products found",
                [],
                0
            )

        return api_response(
            200,
            f"Found {len(enhanced_products)} sale products",
            enhanced_products,
            len(enhanced_products)
        )

    except Exception as e:
        return api_response(500, f"Error fetching sale products: {str(e)}")
    
@router.get("/sales-simple")
def get_sale_products_simple(
    session: GetSession,
    query_params: ListQueryParams,
    is_active: bool = True,
    shop_id: Optional[int] = None,  # Filter by shop
):
    """
    Simple version of sale products with advanced filtering
    """
    try:
        # Extract query params
        query_params_dict = vars(query_params)
        limit = query_params_dict.get('limit', 50)
        page = query_params_dict.get('page', 1)
        skip = (page - 1) * limit
        
        print(f"Fetching sale products: is_active={is_active}, limit={limit}, page={page}")
        
        # SIMPLE PRODUCTS - Direct query without joins first
        simple_condition = and_(
            Product.is_active == is_active,
            Product.product_type == ProductType.SIMPLE,
            Product.sale_price > 0,
            Product.sale_price < Product.price
        )

        simple_products_stmt = select(Product).where(simple_condition)

        # Add shop filter
        if shop_id:
            simple_products_stmt = simple_products_stmt.where(Product.shop_id == shop_id)

        # Apply columnFilters
        if query_params_dict.get('columnFilters'):
            import ast
            column_filters = ast.literal_eval(query_params_dict['columnFilters'])
            for col_filter in column_filters:
                field_name, field_value = col_filter[0], col_filter[1]
                if hasattr(Product, field_name):
                    field = getattr(Product, field_name)
                    if isinstance(field_value, list):
                        simple_products_stmt = simple_products_stmt.where(field.in_(field_value))
                    else:
                        simple_products_stmt = simple_products_stmt.where(field == field_value)

        # Apply searchTerm
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            simple_products_stmt = simple_products_stmt.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        # Apply numberRange filter
        simple_products_stmt = apply_number_range_filter(simple_products_stmt, query_params_dict, Product)

        # Apply sort filter
        simple_products_stmt = apply_sort_filter(simple_products_stmt, query_params_dict, Product, "created_at", "desc")

        simple_products_stmt = (
            simple_products_stmt
            .offset(skip)
            .limit(limit)
        )

        print("Executing simple products query...")
        simple_products = distinct_products(session.exec(simple_products_stmt).all())
        print(f"Found {len(simple_products)} simple products on sale")
        
        # VARIABLE PRODUCTS - Separate query to avoid complex joins
        # First get product IDs that have sale variations
        variable_product_ids_stmt = (
            select(VariationOption.product_id)
            .where(
                and_(
                    VariationOption.sale_price.isnot(None),
                    cast(VariationOption.sale_price, Float) > 0,
                    cast(VariationOption.sale_price, Float) < cast(VariationOption.price, Float)
                )
            )
            .distinct()
        )
        
        print("Getting variable product IDs...")
        variable_product_ids = session.exec(variable_product_ids_stmt).all()
        print(f"Found {len(variable_product_ids)} variable products with sale variations")
        
        # Now get the actual products
        variable_products = []
        if variable_product_ids:
            variable_condition = and_(
                Product.is_active == is_active,
                Product.product_type == ProductType.VARIABLE,
                Product.id.in_(variable_product_ids)
            )

            variable_products_stmt = select(Product).where(variable_condition)

            # Add shop filter
            if shop_id:
                variable_products_stmt = variable_products_stmt.where(Product.shop_id == shop_id)

            # Apply columnFilters
            if query_params_dict.get('columnFilters'):
                import ast
                column_filters = ast.literal_eval(query_params_dict['columnFilters'])
                for col_filter in column_filters:
                    field_name, field_value = col_filter[0], col_filter[1]
                    if hasattr(Product, field_name):
                        field = getattr(Product, field_name)
                        if isinstance(field_value, list):
                            variable_products_stmt = variable_products_stmt.where(field.in_(field_value))
                        else:
                            variable_products_stmt = variable_products_stmt.where(field == field_value)

            # Apply searchTerm
            if query_params_dict.get('searchTerm'):
                search = f"%{query_params_dict['searchTerm']}%"
                variable_products_stmt = variable_products_stmt.where(
                    or_(
                        Product.name.ilike(search),
                        Product.description.ilike(search),
                        Product.sku.ilike(search)
                    )
                )

            # Apply numberRange filter
            variable_products_stmt = apply_number_range_filter(variable_products_stmt, query_params_dict, Product)

            # Apply sort filter
            variable_products_stmt = apply_sort_filter(variable_products_stmt, query_params_dict, Product, "created_at", "desc")

            variable_products_stmt = (
                variable_products_stmt
                .offset(skip)
                .limit(limit)
            )

            print("Executing variable products query...")
            variable_products = distinct_products(session.exec(variable_products_stmt).all())
            print(f"Retrieved {len(variable_products)} variable products")
        
        # Combine results manually - NO list() function calls
        all_products = []
        all_products.extend(simple_products)
        all_products.extend(variable_products)
        
        # Remove duplicates using a dictionary
        unique_products_dict = {}
        for product in all_products:
            unique_products_dict[product.id] = product
        
        # Convert to list using list comprehension - NOT the list() function
        sale_products = [product for product in unique_products_dict.values()]
        
        # Apply limit
        if len(sale_products) > limit:
            sale_products = sale_products[:limit]
        
        print(f"Total unique sale products: {len(sale_products)}")
        
        # Build response - completely manual, no external function calls
        response_data = []
        for product in sale_products:
            try:
                product_data = {
                    "id": product.id,
                    "name": product.name,
                    "slug": product.slug,
                    "price": float(product.price) if product.price else 0.0,
                    "sale_price": float(product.sale_price) if product.sale_price else None,
                    "product_type": product.product_type.value if hasattr(product.product_type, 'value') else str(product.product_type),
                    "is_active": product.is_active,
                    "image": product.image,
                    "category_id": product.category_id,
                    "shop_id": product.shop_id,
                    "quantity": product.quantity
                }
                
                # Calculate discount for simple products
                if (product.product_type == ProductType.SIMPLE and 
                    product.price and product.sale_price and 
                    product.price > 0):
                    discount = ((product.price - product.sale_price) / product.price) * 100
                    product_data['discount_percent'] = round(float(discount), 2)
                else:
                    product_data['discount_percent'] = 0
                
                response_data.append(product_data)
                
            except Exception as product_error:
                print(f"Error processing product {product.id}: {product_error}")
                continue
        
        print(f"Successfully processed {len(response_data)} products for response")

        # Check if no products found
        if not response_data:
            return api_response(
                404,
                "No sale products found",
                [],
                0
            )

        return api_response(
            200,
            f"Found {len(response_data)} sale products",
            response_data,
            len(response_data)
        )

    except Exception as e:
        print(f"CRITICAL ERROR in sales-simple: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return api_response(500, f"Error fetching sale products: {str(e)}")

@router.get("/new-arrivals")
def get_new_arrivals(
    session: GetSession,
    query_params: ListQueryParams,
    is_active: bool = True,
    days: int = 30,  # Products added in last X days
    shop_id: Optional[int] = None,  # Filter by shop
    #user=requirePermission(["product:view", "shop_admin"]),
):
    """
    Get newly added products with advanced filtering and sorting options
    Similar to product/list with additional new arrivals specific filters
    """
    try:
        # Calculate date threshold for new arrivals
        from datetime import datetime, timedelta
        threshold_date = datetime.now() - timedelta(days=days)

        # Extract query params
        query_params_dict = vars(query_params)
        limit = query_params_dict.get('limit', 20)
        page = query_params_dict.get('page', 1)
        skip = (page - 1) * limit

        # Build base query
        query = (
            select(Product)
            .join(Shop, Product.shop_id == Shop.id)
            .where(
                and_(
                    Product.is_active == is_active,
                    Shop.is_active == True,
                    Product.created_at >= threshold_date
                )
            )
        )

        # Add shop filter if provided
        if shop_id:
            query = query.where(Product.shop_id == shop_id)

        # Apply columnFilters from query_params
        if query_params_dict.get('columnFilters'):
            import ast
            column_filters = ast.literal_eval(query_params_dict['columnFilters'])
            for col_filter in column_filters:
                field_name, field_value = col_filter[0], col_filter[1]
                if hasattr(Product, field_name):
                    field = getattr(Product, field_name)
                    if isinstance(field_value, list):
                        query = query.where(field.in_(field_value))
                    else:
                        query = query.where(field == field_value)

        # Apply searchTerm
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            query = query.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        # Apply numberRange filter
        query = apply_number_range_filter(query, query_params_dict, Product)

        # Apply sort filter
        query = apply_sort_filter(query, query_params_dict, Product, "created_at", "desc")
        
        # Execute query
        products = distinct_products(session.exec(
            query
            .offset(skip)
            .limit(limit)
        ).all())

        # Get total count for pagination
        count_query = (
            select(func.count(Product.id))
            .join(Shop, Product.shop_id == Shop.id)
            .where(
                and_(
                    Product.is_active == is_active,
                    Shop.is_active == True,
                    Product.created_at >= threshold_date
                )
            )
        )

        # Apply shop filter to count query
        if shop_id:
            count_query = count_query.where(Product.shop_id == shop_id)

        total_count = session.exec(count_query).first()

        # Get unique enhanced products
        enhanced_products = get_unique_enhanced_products(session, products, return_dict=True)

        # Check if no products found
        if not enhanced_products:
            return api_response(
                404,
                "No new arrival products found",
                [],
                0
            )

        return api_response(
            200,
            f"Found {len(enhanced_products)} new arrival products",
            enhanced_products,
            total_count
        )

    except Exception as e:
        print(f"Error fetching new arrivals: {str(e)}")
        return api_response(500, f"Error fetching new arrivals: {str(e)}")


# PUT /product/updateqtyprice/{id} - Update quantity and/or price
@router.put("/updateqtyprice/{id}")
def update_qty_price(
    id: int,
    request: UpdateQtyPriceRequest,
    session: GetSession,
    user=requirePermission(["product:update", "vendor-product:update"]),
):
    """
    Update product quantity and/or price with transaction logging

    Rules:
    - If quantity > 0: purchase_price is required, sale_price and price are optional
    - If quantity is 0 or null: price is required
    - If sale_price > 0: it must be < price or null
    - notes is required in all conditions
    - If quantity is set: update stock level (previous quantity + quantity = current stock)
    - If price or sale_price is sent: update the price and sale_price
    - For variable products: variation_option_id field is required
    - Keep record in transactionlog if quantity is updated OR if only price/sale_price is sent
    """
    try:
        # Get product
        product = session.get(Product, id)
        raiseExceptions((product, 404, "Product not found"))

        # Check shop ownership
        shop_ids = [s["id"] for s in user.get("shops", [])]
        if product.shop_id not in shop_ids:
            return api_response(403, "You are not authorized to update this product")

        # Initialize transaction logger
        logger = TransactionLogger(session)

        # Validation: Check if it's a variable product
        if product.product_type == ProductType.VARIABLE:
            if not request.variation_option_id:
                return api_response(400, "variation_option_id is required for variable products")

            # Get variation option
            variation = session.get(VariationOption, request.variation_option_id)
            if not variation:
                return api_response(404, "Variation option not found")

            if variation.product_id != product.id:
                return api_response(400, "Variation option does not belong to this product")

            # Validate rules for variable products
            if request.quantity is not None and request.quantity > 0:
                # When adding stock, purchase_price is required
                if request.purchase_price is None or request.purchase_price <= 0:
                    return api_response(400, "purchase_price is required when quantity > 0")
            elif (request.quantity is None or request.quantity == 0) and request.price is not None:
                # When updating price only (no quantity), price is required
                if request.price <= 0:
                    return api_response(400, "price must be greater than 0")

            # Store previous values
            previous_quantity = variation.quantity
            previous_price = float(variation.price) if variation.price else None
            previous_sale_price = float(variation.sale_price) if variation.sale_price else None

            # Update quantity if provided
            if request.quantity is not None and request.quantity > 0:
                variation.quantity += request.quantity
                variation.purchase_price = request.purchase_price

                # Log stock addition for variation
                logger.log_stock_addition(
                    product=product,
                    quantity=request.quantity,
                    purchase_price=request.purchase_price,
                    user_id=user["id"],
                    notes=request.notes,
                    variation_option_id=request.variation_option_id,
                    previous_quantity=previous_quantity,
                    new_quantity=variation.quantity
                )

                # Update main product quantity
                product.quantity += request.quantity

            # Update prices if provided
            price_updated = False
            if request.price is not None:
                variation.price = str(request.price)
                price_updated = True

            if request.sale_price is not None:
                variation.sale_price = str(request.sale_price) if request.sale_price > 0 else None
                price_updated = True

            # Log price change if prices were updated and no quantity change
            if price_updated and (request.quantity is None or request.quantity == 0):
                logger.log_price_change(
                    product=product,
                    previous_price=previous_price,
                    new_price=float(variation.price) if variation.price else None,
                    previous_sale_price=previous_sale_price,
                    new_sale_price=float(variation.sale_price) if variation.sale_price else None,
                    user_id=user["id"],
                    notes=request.notes,
                    variation_option_id=request.variation_option_id
                )

            session.add(variation)
            session.add(product)
            session.commit()
            session.refresh(product)
            session.refresh(variation)

            # Return enhanced product data
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            return api_response(200, "Variation updated successfully", enhanced_product)

        else:
            # Simple product logic
            # Validate rules for simple products
            if request.quantity is not None and request.quantity > 0:
                # When adding stock, purchase_price is required
                if request.purchase_price is None or request.purchase_price <= 0:
                    return api_response(400, "purchase_price is required when quantity > 0")
            elif (request.quantity is None or request.quantity == 0) and request.price is not None:
                # When updating price only (no quantity), price is required
                if request.price <= 0:
                    return api_response(400, "price must be greater than 0")

            # Store previous values
            previous_quantity = product.quantity
            previous_price = product.price
            previous_sale_price = product.sale_price

            # Update quantity if provided
            if request.quantity is not None and request.quantity > 0:
                product.quantity += request.quantity
                product.purchase_price = request.purchase_price

                # Log stock addition
                logger.log_stock_addition(
                    product=product,
                    quantity=request.quantity,
                    purchase_price=request.purchase_price,
                    user_id=user["id"],
                    notes=request.notes,
                    previous_quantity=previous_quantity,
                    new_quantity=product.quantity
                )

            # Update prices if provided
            price_updated = False
            if request.price is not None:
                product.price = request.price
                price_updated = True

            if request.sale_price is not None:
                product.sale_price = request.sale_price if request.sale_price > 0 else None
                price_updated = True

            # Log price change if prices were updated and no quantity change
            if price_updated and (request.quantity is None or request.quantity == 0):
                logger.log_price_change(
                    product=product,
                    previous_price=previous_price,
                    new_price=product.price,
                    previous_sale_price=previous_sale_price,
                    new_sale_price=product.sale_price,
                    user_id=user["id"],
                    notes=request.notes
                )

            # Update stock status
            product.in_stock = product.quantity > 0

            session.add(product)
            session.commit()
            session.refresh(product)

            # Return enhanced product data
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            return api_response(200, "Product updated successfully", enhanced_product)

    except ValueError as ve:
        return api_response(400, str(ve))
    except Exception as e:
        session.rollback()
        print(f"Error updating product quantity/price: {str(e)}")
        return api_response(500, f"Error updating product: {str(e)}")


# PATCH /product/removeqty/{id} - Remove quantity from product
@router.patch("/removeqty/{id}")
def remove_qty(
    id: int,
    request: RemoveQtyRequest,
    session: GetSession,
    user=requirePermission(["product:update", "vendor-product:update"]),
):
    """
    Remove quantity from product stock with transaction logging

    Rules:
    - quantity and notes are required
    - quantity is subtracted from the stock
    - Simple product is updated by product_id
    - Variable product can be updated single or bulk via variation_option_id
    - Keep record in transactionlog
    """
    try:
        # Get product
        product = session.get(Product, id)
        raiseExceptions((product, 404, "Product not found"))

        # Check shop ownership
        shop_ids = [s["id"] for s in user.get("shops", [])]
        if product.shop_id not in shop_ids:
            return api_response(403, "You are not authorized to update this product")

        # Initialize transaction logger
        logger = TransactionLogger(session)

        # Check if it's a variable product
        if product.product_type == ProductType.VARIABLE:
            if not request.variation_option_id:
                return api_response(400, "variation_option_id is required for variable products")

            # Get variation option
            variation = session.get(VariationOption, request.variation_option_id)
            if not variation:
                return api_response(404, "Variation option not found")

            if variation.product_id != product.id:
                return api_response(400, "Variation option does not belong to this product")

            # Check if there's enough stock
            if variation.quantity < request.quantity:
                return api_response(
                    400,
                    f"Insufficient stock. Available: {variation.quantity}, Requested: {request.quantity}"
                )

            # Store previous quantity
            previous_quantity = variation.quantity

            # Deduct quantity
            variation.quantity -= request.quantity

            # Log stock deduction for variation
            logger.log_stock_deduction(
                product=product,
                quantity=request.quantity,
                user_id=user["id"],
                notes=request.notes,
                variation_option_id=request.variation_option_id,
                previous_quantity=previous_quantity,
                new_quantity=variation.quantity
            )

            # Update main product quantity
            product.quantity -= request.quantity

            # Update stock status
            product.in_stock = product.quantity > 0

            session.add(variation)
            session.add(product)
            session.commit()
            session.refresh(product)
            session.refresh(variation)

            # Return enhanced product data
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            return api_response(200, "Variation quantity removed successfully", enhanced_product)

        else:
            # Simple product logic
            # Check if there's enough stock
            if product.quantity < request.quantity:
                return api_response(
                    400,
                    f"Insufficient stock. Available: {product.quantity}, Requested: {request.quantity}"
                )

            # Store previous quantity
            previous_quantity = product.quantity

            # Deduct quantity
            product.quantity -= request.quantity

            # Log stock deduction
            logger.log_stock_deduction(
                product=product,
                quantity=request.quantity,
                user_id=user["id"],
                notes=request.notes,
                previous_quantity=previous_quantity,
                new_quantity=product.quantity
            )

            # Update stock status
            product.in_stock = product.quantity > 0

            session.add(product)
            session.commit()
            session.refresh(product)

            # Return enhanced product data
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            return api_response(200, "Product quantity removed successfully", enhanced_product)

    except ValueError as ve:
        return api_response(400, str(ve))
    except Exception as e:
        session.rollback()
        print(f"Error removing product quantity: {str(e)}")
        return api_response(500, f"Error removing quantity: {str(e)}")


# Pydantic schema for inventory response
class ProductInventoryRead(BaseModel):
    id: int
    name: str
    slug: str
    product_type: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    manufacturer_id: Optional[int] = None
    manufacturer_name: Optional[str] = None
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    current_stock: int
    total_sold: int
    price: Optional[float] = None
    sale_price: Optional[float] = None

    class Config:
        from_attributes = True


@router.get("/inventory")
def get_product_inventory(
    session: GetSession,
    query_params: ListQueryParams,
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    manufacturer_id: Optional[int] = Query(None, description="Filter by manufacturer ID"),
    shop_id: Optional[int] = Query(None, description="Filter by shop ID"),
    product_type: Optional[str] = Query(None, description="Filter by product type (simple, variable, grouped)"),
    product_name: Optional[str] = Query(None, description="Filter by product name (partial match)"),
    min_price: Optional[float] = Query(None, description="Filter by minimum price"),
    max_price: Optional[float] = Query(None, description="Filter by maximum price"),
    min_quantity: Optional[int] = Query(None, description="Filter by minimum quantity/stock"),
    max_quantity: Optional[int] = Query(None, description="Filter by maximum quantity/stock"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    user=requirePermission(["product:view", "vendor-product:view"]),
):
    """
    Get product inventory with filters for:
    - category
    - manufacturer
    - shop
    - product_type
    - product_name
    - price range
    - quantity/stock range

    Returns list of products with:
    - id, name, slug, product_type
    - category name
    - manufacturer name
    - shop name
    - current_stock (quantity)
    - total_sold

    Note: Users can only view inventory from their own shops unless they have
    "inventory:view" permission and role_id is not in [2, 4, 5, 6].
    """
    try:
        # Extract query params
        query_params_dict = vars(query_params)
        limit = query_params_dict.get('limit', 50)
        page = query_params_dict.get('page', 1)
        skip = (page - 1) * limit

        # Check if user can bypass shop ownership check
        # User must have "inventory:view" permission AND role_id NOT in [2, 4, 5, 6]
        user_permissions = user.get("permissions", [])
        user_role_id = user.get("role_id")
        restricted_role_ids = [2, 4, 5, 6]

        has_inventory_view = "inventory:view" in user_permissions
        can_bypass_shop_check = has_inventory_view and user_role_id not in restricted_role_ids

        # Get user's shop IDs for filtering
        user_shop_ids = [s["id"] for s in user.get("shops", [])]

        if can_bypass_shop_check:
            # User can view all shops - no shop filtering needed
            if shop_id is not None:
                # If specific shop_id provided, filter by that shop only
                filter_shop_ids = [shop_id]
            else:
                # No shop filter - view all products
                filter_shop_ids = None
        else:
            # Regular users - must filter by their own shops
            if shop_id is not None:
                if shop_id not in user_shop_ids:
                    return api_response(403, "Access denied to specified shop")
                filter_shop_ids = [shop_id]
            else:
                filter_shop_ids = user_shop_ids

            # If user has no shops, return empty result
            if not filter_shop_ids:
                return api_response(200, "No shops found for user", [], 0)

        # Build base query with joins for related data
        query = (
            select(
                Product.id,
                Product.name,
                Product.slug,
                Product.product_type,
                Product.category_id,
                Category.name.label("category_name"),
                Product.manufacturer_id,
                Manufacturer.name.label("manufacturer_name"),
                Product.shop_id,
                Shop.name.label("shop_name"),
                Product.quantity.label("current_stock"),
                Product.total_sold_quantity.label("total_sold"),
                Product.price,
                Product.sale_price,
            )
            .outerjoin(Category, Product.category_id == Category.id)
            .outerjoin(Manufacturer, Product.manufacturer_id == Manufacturer.id)
            .outerjoin(Shop, Product.shop_id == Shop.id)
        )

        # Apply shop filter only if filter_shop_ids is not None
        if filter_shop_ids is not None:
            query = query.where(Product.shop_id.in_(filter_shop_ids))

        # Apply filters
        if category_id is not None:
            query = query.where(Product.category_id == category_id)

        if manufacturer_id is not None:
            query = query.where(Product.manufacturer_id == manufacturer_id)

        if product_type is not None:
            # Map string to ProductType enum
            product_type_upper = product_type.upper()
            if product_type_upper == "SIMPLE":
                query = query.where(Product.product_type == ProductType.SIMPLE)
            elif product_type_upper == "VARIABLE":
                query = query.where(Product.product_type == ProductType.VARIABLE)
            elif product_type_upper == "GROUPED":
                query = query.where(Product.product_type == ProductType.GROUPED)

        if product_name is not None:
            search = f"%{product_name}%"
            query = query.where(Product.name.ilike(search))

        if min_price is not None:
            query = query.where(Product.price >= min_price)

        if max_price is not None:
            query = query.where(Product.price <= max_price)

        if min_quantity is not None:
            query = query.where(Product.quantity >= min_quantity)

        if max_quantity is not None:
            query = query.where(Product.quantity <= max_quantity)

        if is_active is not None:
            query = query.where(Product.is_active == is_active)

        # Apply searchTerm from query_params (searches name, description, sku)
        if query_params_dict.get('searchTerm'):
            search = f"%{query_params_dict['searchTerm']}%"
            query = query.where(
                or_(
                    Product.name.ilike(search),
                    Product.description.ilike(search),
                    Product.sku.ilike(search)
                )
            )

        # Apply columnFilters from query_params
        if query_params_dict.get('columnFilters'):
            import ast
            column_filters = ast.literal_eval(query_params_dict['columnFilters'])
            for col_filter in column_filters:
                field_name, field_value = col_filter[0], col_filter[1]
                if hasattr(Product, field_name):
                    field = getattr(Product, field_name)
                    if isinstance(field_value, list):
                        query = query.where(field.in_(field_value))
                    else:
                        query = query.where(field == field_value)

        # Apply numberRange filter
        query = apply_number_range_filter(query, query_params_dict, Product)

        # Apply sort filter (default: sort by name ascending)
        query = apply_sort_filter(query, query_params_dict, Product, "name", "asc")

        # Get total count for pagination
        count_query = select(func.count(Product.id))

        # Apply shop filter to count query only if filter_shop_ids is not None
        if filter_shop_ids is not None:
            count_query = count_query.where(Product.shop_id.in_(filter_shop_ids))

        # Apply same filters to count query
        if category_id is not None:
            count_query = count_query.where(Product.category_id == category_id)
        if manufacturer_id is not None:
            count_query = count_query.where(Product.manufacturer_id == manufacturer_id)
        if product_type is not None:
            product_type_upper = product_type.upper()
            if product_type_upper == "SIMPLE":
                count_query = count_query.where(Product.product_type == ProductType.SIMPLE)
            elif product_type_upper == "VARIABLE":
                count_query = count_query.where(Product.product_type == ProductType.VARIABLE)
            elif product_type_upper == "GROUPED":
                count_query = count_query.where(Product.product_type == ProductType.GROUPED)
        if product_name is not None:
            count_query = count_query.where(Product.name.ilike(f"%{product_name}%"))
        if min_price is not None:
            count_query = count_query.where(Product.price >= min_price)
        if max_price is not None:
            count_query = count_query.where(Product.price <= max_price)
        if min_quantity is not None:
            count_query = count_query.where(Product.quantity >= min_quantity)
        if max_quantity is not None:
            count_query = count_query.where(Product.quantity <= max_quantity)
        if is_active is not None:
            count_query = count_query.where(Product.is_active == is_active)

        total_count = session.exec(count_query).first() or 0

        # Execute main query with pagination
        query = query.offset(skip).limit(limit)
        raw_results = session.exec(query).all()
        # Deduplicate by product id
        seen_inv = set()
        results = []
        for row in raw_results:
            if row.id not in seen_inv:
                seen_inv.add(row.id)
                results.append(row)

        # Build response data
        inventory_list = []
        for row in results:
            inventory_item = ProductInventoryRead(
                id=row.id,
                name=row.name,
                slug=row.slug,
                product_type=row.product_type.value if hasattr(row.product_type, 'value') else str(row.product_type),
                category_id=row.category_id,
                category_name=row.category_name,
                manufacturer_id=row.manufacturer_id,
                manufacturer_name=row.manufacturer_name,
                shop_id=row.shop_id,
                shop_name=row.shop_name,
                current_stock=row.current_stock or 0,
                total_sold=row.total_sold or 0,
                price=row.price,
                sale_price=row.sale_price,
            )
            inventory_list.append(inventory_item.model_dump())

        return api_response(
            200,
            f"Found {len(inventory_list)} products",
            inventory_list,
            total_count
        )

    except Exception as e:
        print(f"Error fetching product inventory: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return api_response(500, f"Error fetching product inventory: {str(e)}")