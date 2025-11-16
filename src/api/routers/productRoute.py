from fastapi import APIRouter
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


@router.get("/trending")
def get_trending_products(
    session: GetSession,
    limit: int = 10,
    days: int = 30  # Trending in last X days
):
    """
    Get trending products based on sales in recent days
    """
    try:
        # Calculate date threshold
        from datetime import datetime, timedelta
        threshold_date = datetime.now() - timedelta(days=days)
        
        # Query products with highest sales in recent period
        # Using total_sold_quantity as a proxy for trending
        query = (
            select(Product)
            .where(
                and_(
                    Product.is_active == True,
                    Product.total_sold_quantity > 0,
                    Product.created_at >= threshold_date
                )
            )
            .order_by(Product.total_sold_quantity.desc())
            .limit(limit)
        )
        
        products = session.exec(query).all()
        
        enhanced_products = []
        for product in products:
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            if enhanced_product:
                enhanced_products.append(enhanced_product)
        
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
    limit: int = 10,
    low_stock_threshold: int = 20
):
    """
    Get limited edition products (low stock items)
    """
    try:
        query = (
            select(Product)
            .where(
                and_(
                    Product.is_active == True,
                    Product.quantity > 0,
                    Product.quantity <= low_stock_threshold
                )
            )
            .order_by(Product.quantity.asc())  # Lowest quantity first
            .limit(limit)
        )
        
        products = session.exec(query).all()
        
        enhanced_products = []
        for product in products:
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            if enhanced_product:
                enhanced_products.append(enhanced_product)
        
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
    limit: int = 10,
    days: Optional[int] = None  # Optional: best sellers in specific period
):
    """
    Get best seller products based on total sold quantity
    """
    try:
        query = select(Product).where(Product.is_active == True)
        
        # If days parameter provided, filter by date
        if days:
            from datetime import datetime, timedelta
            threshold_date = datetime.now() - timedelta(days=days)
            query = query.where(Product.created_at >= threshold_date)
        
        query = (
            query
            .where(Product.total_sold_quantity > 0)
            .order_by(Product.total_sold_quantity.desc())
            .limit(limit)
        )
        
        products = session.exec(query).all()
        
        enhanced_products = []
        for product in products:
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            if enhanced_product:
                enhanced_products.append(enhanced_product)
        
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
    is_active: bool = True,  # Filter by active status
    limit: int = 50,
    page: int = 1,
    user=requirePermission("product_view", "shop_admin"),
):
    """
    Get products that are on sale
    - For simple products: sale_price > 0 and sale_price < price
    - For variable products: variation options with sale_price > 0 and sale_price < price
    - Includes is_active filter
    """
    try:
        skip = (page - 1) * limit
        
        # Build base query for simple products on sale
        simple_products_query = (
            select(Product)
            .where(
                and_(
                    Product.is_active == is_active,
                    Product.product_type == ProductType.SIMPLE,
                    Product.sale_price > 0,
                    Product.sale_price < Product.price,
                    Product.price > 0  # Ensure price is valid
                )
            )
        )

        # Filter by user's shops if applicable
        shop_ids = [s["id"] for s in user.get("shops", [])]
        if shop_ids:
            simple_products_query = simple_products_query.where(Product.shop_id.in_(shop_ids))

        # Get simple products on sale
        simple_products = session.exec(
            simple_products_query
            .offset(skip)
            .limit(limit)
        ).all()

        # Query for variable products that have variations on sale
        variable_products_query = (
            select(Product)
            .join(VariationOption, Product.id == VariationOption.product_id)
            .where(
                and_(
                    Product.is_active == is_active,
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

        # Filter by user's shops if applicable
        if shop_ids:
            variable_products_query = variable_products_query.where(Product.shop_id.in_(shop_ids))

        # Get variable products with sale variations
        variable_products = session.exec(
            variable_products_query
            .offset(skip)
            .limit(limit)
        ).all()

        # Combine and deduplicate products
        all_products = simple_products + variable_products
        unique_products = {product.id: product for product in all_products}.values()

        # Convert to list and limit results
        sale_products = list(unique_products)[:limit]

        # Enhance product data
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
    is_active: bool = True,
    limit: int = 50,
    page: int = 1,
    product_type: Optional[str] = None,  # Optional filter by product type
    user=requirePermission("product_view", "shop_admin"),
):
    """
    Optimized version of sale products query
    """
    try:
        skip = (page - 1) * limit
        
        # Build the main query
        query = select(Product).where(Product.is_active == is_active)
        
        # Filter by user's shops
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
        
        # Add ordering by discount amount (highest discount first)
        from sqlalchemy import case
        
        discount_case = case(
            (Product.product_type == ProductType.SIMPLE, 
             (Product.price - Product.sale_price) / Product.price * 100),
            else_=0
        ).label('discount_percent')
        
        query = query.order_by(discount_case.desc())
        
        # Execute query
        products = session.exec(
            query
            .offset(skip)
            .limit(limit)
        ).all()
        
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
        
        return api_response(
            200,
            f"Found {len(enhanced_products)} sale products",
            {
                "products": enhanced_products,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit if total_count else 0
                }
            }
        )
        
    except Exception as e:
        print(f"Error in optimized sale products: {str(e)}")
        return api_response(500, f"Error fetching sale products: {str(e)}")


# Simple version for public access (without shop filtering)
@router.get("/sales/public")
def get_public_sale_products(
    session: GetSession,
    is_active: bool = True,
    limit: int = 20,
    page: int = 1
):
    """
    Public endpoint for sale products (no authentication required)
    """
    try:
        skip = (page - 1) * limit
        
        # Simple products on sale
        simple_products = session.exec(
            select(Product)
            .where(
                and_(
                    Product.is_active == is_active,
                    Product.product_type == ProductType.SIMPLE,
                    Product.sale_price > 0,
                    Product.sale_price < Product.price
                )
            )
            .offset(skip)
            .limit(limit)
        ).all()
        
        # Variable products with sale variations
        variable_products = session.exec(
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
            .offset(skip)
            .limit(limit)
        ).all()
        
        # Combine results
        all_products = simple_products + variable_products
        unique_products = {product.id: product for product in all_products}.values()
        sale_products = list(unique_products)[:limit]
        
        # Enhance data - FIX: Pass session parameter
        enhanced_products = []
        for product in sale_products:
            # FIX: Pass the session parameter
            enhanced_product = get_product_with_enhanced_data(session, product.id)
            if enhanced_product:
                enhanced_products.append(enhanced_product.model_dump())
        
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
    is_active: bool = True,
    limit: int = 50,
    page: int = 1,
):
    """
    Simple version of sale products without complex enhancements
    """
    try:
        skip = (page - 1) * limit
        
        print(f"Fetching sale products: is_active={is_active}, limit={limit}, page={page}")
        
        # SIMPLE PRODUCTS - Direct query without joins first
        simple_condition = and_(
            Product.is_active == is_active,
            Product.product_type == ProductType.SIMPLE,
            Product.sale_price > 0,
            Product.sale_price < Product.price
        )
        
        simple_products_stmt = (
            select(Product)
            .where(simple_condition)
            .offset(skip)
            .limit(limit)
        )
        
        print("Executing simple products query...")
        simple_products = session.exec(simple_products_stmt).all()
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
            
            variable_products_stmt = (
                select(Product)
                .where(variable_condition)
                .offset(skip)
                .limit(limit)
            )
            
            print("Executing variable products query...")
            variable_products = session.exec(variable_products_stmt).all()
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