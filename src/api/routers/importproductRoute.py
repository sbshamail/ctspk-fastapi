# src/api/routes/product_import.py
import pandas as pd
import io
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, Query
from sqlmodel import Session, select, desc, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from src.api.core.dependencies import GetSession, requirePermission
from src.api.core.response import api_response, raiseExceptions
from src.api.models.product_model.productsModel import (
    Product, ProductType, ProductStatus,
    ProductAttribute, VariationData, GroupedProductItem
)
from src.api.models.product_model.importHistoryModel import ProductImportHistory
from src.api.models.category_model.categoryModel import Category
from src.api.models.manufacturer_model.manufacturerModel import Manufacturer
from src.api.models.product_model.variationOptionModel import VariationOption
from src.api.core.utility import uniqueSlugify
from src.api.core.sku_generator import generate_unique_sku

router = APIRouter(prefix="/product", tags=["Product Import"])

class ProductImportService:
    def __init__(self, session: Session, import_history_id: int = None):
        self.session = session
        self.import_history_id = import_history_id
        self.categories_map = {}
        self.manufacturers_map = {}
        self.attributes_map = {}
        
    def load_reference_data(self):
        """Load categories, manufacturers, and attributes for mapping"""
        # Load categories
        categories = self.session.exec(select(Category)).all()
        self.categories_map = {cat.name.lower(): cat.id for cat in categories}
        
        # Load manufacturers
        manufacturers = self.session.exec(select(Manufacturer)).all()
        self.manufacturers_map = {mfg.name.lower(): mfg.id for mfg in manufacturers}
        
    def update_import_history(self, status: str = None, errors: List = None, imported_products: List = None):
        """Update import history record"""
        if not self.import_history_id:
            return
            
        import_history = self.session.get(ProductImportHistory, self.import_history_id)
        if not import_history:
            return
            
        if status:
            import_history.status = status
            if status == "completed":
                import_history.completed_at = datetime.now(timezone.utc)
                
        if errors is not None:
            import_history.import_errors = errors
            
        if imported_products is not None:
            import_history.imported_products = imported_products
            
        import_history.successful_records = len(imported_products or [])
        import_history.failed_records = len(errors or [])
        
        self.session.add(import_history)
        self.session.commit()
    
    def get_category_id(self, category_name: str) -> int:
        """Get category ID by name, create if not exists"""
        if not category_name:
            raise ValueError("Category name is required")
            
        category_key = category_name.strip().lower()
        
        if category_key in self.categories_map:
            return self.categories_map[category_key]
            
        # Create new category
        new_category = Category(
            name=category_name.strip(),
            slug=uniqueSlugify(self.session, Category, category_name.strip()),
            is_active=True
        )
        self.session.add(new_category)
        self.session.commit()
        self.session.refresh(new_category)
        
        self.categories_map[category_key] = new_category.id
        return new_category.id
    
    def get_manufacturer_id(self, manufacturer_name: str) -> int:
        """Get manufacturer ID by name"""
        if not manufacturer_name:
            return None
            
        manufacturer_key = manufacturer_name.strip().lower()
        return self.manufacturers_map.get(manufacturer_key)

    def parse_simple_product(self, row: pd.Series, shop_id: int) -> Dict[str, Any]:
        """Parse simple product data from Excel row"""
        try:
            # Required fields
            name = str(row['name']).strip()
            if not name:
                raise ValueError("Product name is required")
                
            price = float(row['price']) if pd.notna(row['price']) else 0
            category_name = str(row['category']).strip()
            
            category_id = self.get_category_id(category_name)
            manufacturer_id = self.get_manufacturer_id(str(row.get('manufacturer', '')).strip())
            
            # Optional fields with defaults
            description = str(row.get('description', '')).strip()
            sku = str(row.get('sku', '')).strip() or generate_unique_sku(self.session)
            bar_code = str(row.get('bar_code', '')).strip()
            quantity = int(row.get('quantity', 0)) if pd.notna(row.get('quantity')) else 0
            weight = float(row.get('weight', 0)) if pd.notna(row.get('weight')) else None
            sale_price = float(row.get('sale_price')) if pd.notna(row.get('sale_price')) else None
            purchase_price = float(row.get('purchase_price')) if pd.notna(row.get('purchase_price')) else None
            unit = str(row.get('unit', 'pcs')).strip()
            tags = [tag.strip() for tag in str(row.get('tags', '')).split(',') if tag.strip()]
            
            return {
                'name': name,
                'description': description,
                'price': price,
                'sale_price': sale_price,
                'purchase_price': purchase_price,
                'quantity': quantity,
                'weight': weight,
                'category_id': category_id,
                'manufacturer_id': manufacturer_id,
                'sku': sku,
                'bar_code': bar_code,
                'unit': unit,
                'tags': tags,
                'product_type': ProductType.SIMPLE,
                'status': ProductStatus.PUBLISH,
                'shop_id': shop_id,
                'min_price': price,
                'max_price': price
            }
        except Exception as e:
            raise ValueError(f"Error parsing simple product: {str(e)}")
    
    def parse_variable_product(self, df: pd.DataFrame, shop_id: int) -> Dict[str, Any]:
        """Parse variable product data from Excel"""
        try:
            # Get main product data from first row
            main_row = df.iloc[0]
            
            name = str(main_row['name']).strip()
            if not name:
                raise ValueError("Product name is required")
                
            category_name = str(main_row['category']).strip()
            category_id = self.get_category_id(category_name)
            manufacturer_id = self.get_manufacturer_id(str(main_row.get('manufacturer', '')).strip())
            
            # Parse attributes
            attributes = self.parse_attributes(df)
            
            # Parse variations
            variations = self.parse_variations(df, name)
            
            # Calculate min/max prices from variations
            prices = [var.price for var in variations]
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            
            return {
                'name': name,
                'description': str(main_row.get('description', '')).strip(),
                'category_id': category_id,
                'manufacturer_id': manufacturer_id,
                'product_type': ProductType.VARIABLE,
                'status': ProductStatus.PUBLISH,
                'shop_id': shop_id,
                'sku': generate_unique_sku(self.session),
                'min_price': min_price,
                'max_price': max_price,
                'attributes': attributes,
                'variations': variations
            }
        except Exception as e:
            raise ValueError(f"Error parsing variable product: {str(e)}")
    
    def parse_attributes(self, df: pd.DataFrame) -> List[ProductAttribute]:
        """Parse product attributes from Excel data"""
        attributes = []
        
        # Find attribute columns (columns that start with 'attribute_')
        attribute_cols = [col for col in df.columns if col.startswith('attribute_')]
        
        for attr_col in attribute_cols:
            attr_name = attr_col.replace('attribute_', '').replace('_', ' ').title()
            
            # Get unique values for this attribute
            values = df[attr_col].dropna().unique()
            attribute_values = []
            
            for idx, value in enumerate(values):
                attribute_values.append({
                    'id': idx + 1,
                    'value': str(value).strip(),
                    'meta': None
                })
            
            attributes.append(ProductAttribute(
                id=hash(attr_name) % 10000,  # Simple hash for ID
                name=attr_name,
                values=attribute_values,
                is_visible=True,
                is_variation=True
            ))
        
        return attributes
    
    def parse_variations(self, df: pd.DataFrame, product_name: str) -> List[VariationData]:
        """Parse product variations from Excel data"""
        variations = []
        
        for idx, row in df.iterrows():
            try:
                # Get attribute values for this variation
                attributes = []
                attribute_cols = [col for col in df.columns if col.startswith('attribute_')]
                
                for attr_col in attribute_cols:
                    if pd.notna(row[attr_col]):
                        attr_name = attr_col.replace('attribute_', '').replace('_', ' ').title()
                        attributes.append({
                            'attribute_name': attr_name,
                            'value': str(row[attr_col]).strip(),
                            'attribute_id': hash(attr_name) % 10000,
                            'value_id': hash(str(row[attr_col]).strip()) % 10000
                        })
                
                # Variation-specific data
                price = float(row['price']) if pd.notna(row['price']) else 0
                quantity = int(row.get('quantity', 0)) if pd.notna(row.get('quantity')) else 0
                sale_price = float(row.get('sale_price')) if pd.notna(row.get('sale_price')) else None
                purchase_price = float(row.get('purchase_price')) if pd.notna(row.get('purchase_price')) else None
                sku = str(row.get('sku', '')).strip() or f"{generate_unique_sku(self.session)}-V{idx+1}"
                bar_code = str(row.get('bar_code', '')).strip()
                
                variations.append(VariationData(
                    id=f"temp-{idx}",
                    attributes=attributes,
                    price=price,
                    sale_price=sale_price,
                    purchase_price=purchase_price,
                    quantity=quantity,
                    sku=sku,
                    bar_code=bar_code,
                    is_active=True
                ))
                
            except Exception as e:
                raise ValueError(f"Error parsing variation row {idx + 2}: {str(e)}")
        
        return variations
    
    def parse_grouped_product(self, df: pd.DataFrame, shop_id: int) -> Dict[str, Any]:
        """Parse grouped product data from Excel"""
        try:
            # Get main product data from first row
            main_row = df.iloc[0]
            
            name = str(main_row['name']).strip()
            if not name:
                raise ValueError("Product name is required")
                
            category_name = str(main_row['category']).strip()
            category_id = self.get_category_id(category_name)
            manufacturer_id = self.get_manufacturer_id(str(main_row.get('manufacturer', '')).strip())
            
            # Parse grouped products
            grouped_products = self.parse_grouped_products(df)
            
            return {
                'name': name,
                'description': str(main_row.get('description', '')).strip(),
                'category_id': category_id,
                'manufacturer_id': manufacturer_id,
                'product_type': ProductType.GROUPED,
                'status': ProductStatus.PUBLISH,
                'shop_id': shop_id,
                'sku': generate_unique_sku(self.session),
                'min_price': 0,
                'max_price': 0,
                'grouped_products': grouped_products
            }
        except Exception as e:
            raise ValueError(f"Error parsing grouped product: {str(e)}")
    
    def parse_grouped_products(self, df: pd.DataFrame) -> List[GroupedProductItem]:
        """Parse grouped products from Excel data"""
        grouped_products = []
        
        for idx, row in df.iterrows():
            try:
                product_id_str = str(row.get('grouped_product_id', '')).strip()
                if not product_id_str:
                    continue
                    
                # Try to find product by ID or SKU
                product = self.session.exec(
                    select(Product).where(
                        (Product.id == int(product_id_str)) | 
                        (Product.sku == product_id_str)
                    )
                ).first()
                
                if not product:
                    raise ValueError(f"Product not found: {product_id_str}")
                
                quantity = int(row.get('quantity', 1)) if pd.notna(row.get('quantity')) else 1
                
                grouped_products.append(GroupedProductItem(
                    product_id=product.id,
                    quantity=quantity
                ))
                
            except Exception as e:
                raise ValueError(f"Error parsing grouped product row {idx + 2}: {str(e)}")
        
        return grouped_products
    
    def create_product(self, product_data: Dict[str, Any]) -> Product:
        """Create product in database"""
        try:
            # Create main product
            product = Product(
                name=product_data['name'],
                description=product_data.get('description', ''),
                price=product_data.get('price', 0),
                sale_price=product_data.get('sale_price'),
                purchase_price=product_data.get('purchase_price'),
                quantity=product_data.get('quantity', 0),
                weight=product_data.get('weight'),
                category_id=product_data['category_id'],
                manufacturer_id=product_data.get('manufacturer_id'),
                sku=product_data.get('sku', generate_unique_sku(self.session)),
                bar_code=product_data.get('bar_code'),
                unit=product_data.get('unit', 'pcs'),
                tags=product_data.get('tags', []),
                product_type=product_data['product_type'],
                status=product_data.get('status', ProductStatus.PUBLISH),
                shop_id=product_data['shop_id'],
                min_price=product_data.get('min_price', 0),
                max_price=product_data.get('max_price', 0),
                slug=uniqueSlugify(self.session, Product, product_data['name'])
            )
            
            # Add attributes for variable products
            if product_data['product_type'] == ProductType.VARIABLE and 'attributes' in product_data:
                product.attributes = [attr.dict() for attr in product_data['attributes']]
            
            # Add grouped products for grouped products
            if product_data['product_type'] == ProductType.GROUPED and 'grouped_products' in product_data:
                product.grouped_products = [item.dict() for item in product_data['grouped_products']]
            
            self.session.add(product)
            self.session.commit()
            self.session.refresh(product)
            
            # Create variations for variable products
            if product_data['product_type'] == ProductType.VARIABLE and 'variations' in product_data:
                self.create_variations(product.id, product_data['variations'])
            
            return product
            
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error creating product: {str(e)}")
    
    def create_variations(self, product_id: int, variations: List[VariationData]):
        """Create variation options for variable product"""
        for variation in variations:
            try:
                # Create title from attributes
                attribute_names = []
                for attr in variation.attributes:
                    attribute_names.append(f"{attr['attribute_name']}: {attr['value']}")
                
                title = " - ".join(attribute_names)
                
                variation_option = VariationOption(
                    title=title,
                    price=str(variation.price),
                    sale_price=str(variation.sale_price) if variation.sale_price else None,
                    purchase_price=variation.purchase_price,
                    quantity=variation.quantity,
                    product_id=product_id,
                    options={attr['attribute_name']: attr['value'] for attr in variation.attributes},
                    sku=variation.sku,
                    bar_code=variation.bar_code,
                    is_active=variation.is_active
                )
                
                self.session.add(variation_option)
                
            except Exception as e:
                raise ValueError(f"Error creating variation: {str(e)}")
        
        self.session.commit()

def get_user_shop_id(user: dict) -> int:
    """Safely get shop ID from user data"""
    shops = user.get("shops", [])
    print('user',user);
    print('shops',shops);
    if not shops:
        raise ValueError("User is not associated with any shop")
    
    shop_id = shops[0].get("id") if shops else None
    if not shop_id:
        raise ValueError("Shop ID not found in user data")
    
    return shop_id

@router.post("/import-excel")
def import_products_from_excel(
    session: GetSession,
    file: UploadFile = File(...),
    user=requirePermission("product_create", "shop_admin"),
):
    """
    Import products from Excel file with history tracking
    """
    import_history = None
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            return api_response(400, "Only Excel files (.xlsx, .xls) are supported")
        
        # Get shop ID from user - with safe handling
        try:
            shop_id = get_user_shop_id(user)
        except ValueError as e:
            return api_response(400, str(e))
        
        # Create import history record
        import_history = ProductImportHistory(
            filename=f"import_{uuid.uuid4().hex[:8]}.xlsx",
            original_filename=file.filename,
            file_size=0,  # Will be updated after reading file
            shop_id=shop_id,
            imported_by=user.get("id"),
            status="processing"
        )
        session.add(import_history)
        session.commit()
        session.refresh(import_history)
        
        # Read Excel file
        contents = file.file.read()
        excel_file = io.BytesIO(contents)
        
        # Update file size
        import_history.file_size = len(contents)
        session.add(import_history)
        session.commit()
        
        # Initialize import service with history tracking
        import_service = ProductImportService(session, import_history.id)
        import_service.load_reference_data()
        
        # Read all sheets
        xl = pd.ExcelFile(excel_file)
        results = {
            'successful': 0,
            'failed': 0,
            'errors': [],
            'imported_products': []
        }
        
        # Process each sheet
        for sheet_name in xl.sheet_names:
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # Skip empty sheets
                if df.empty:
                    continue
                
                # Update total records
                import_history.total_records += len(df)
                session.add(import_history)
                session.commit()
                
                # Determine product type from sheet name or data
                product_type = None
                if 'variable' in sheet_name.lower():
                    product_type = ProductType.VARIABLE
                elif 'grouped' in sheet_name.lower():
                    product_type = ProductType.GROUPED
                else:
                    product_type = ProductType.SIMPLE
                
                # Process based on product type
                if product_type == ProductType.SIMPLE:
                    # Process each row as separate simple product
                    for idx, row in df.iterrows():
                        try:
                            product_data = import_service.parse_simple_product(row, shop_id)
                            product = import_service.create_product(product_data)
                            results['successful'] += 1
                            results['imported_products'].append({
                                'product_id': product.id,
                                'name': product.name,
                                'sku': product.sku,
                                'type': 'simple',
                                'sheet': sheet_name,
                                'row': idx + 2
                            })
                        except Exception as e:
                            results['failed'] += 1
                            error_msg = f"Sheet '{sheet_name}', Row {idx + 2}: {str(e)}"
                            results['errors'].append(error_msg)
                
                elif product_type == ProductType.VARIABLE:
                    # Process entire sheet as one variable product
                    try:
                        product_data = import_service.parse_variable_product(df, shop_id)
                        product = import_service.create_product(product_data)
                        results['successful'] += 1
                        results['imported_products'].append({
                            'product_id': product.id,
                            'name': product.name,
                            'sku': product.sku,
                            'type': 'variable',
                            'sheet': sheet_name,
                            'variations': len(product_data.get('variations', []))
                        })
                    except Exception as e:
                        results['failed'] += 1
                        error_msg = f"Sheet '{sheet_name}': {str(e)}"
                        results['errors'].append(error_msg)
                
                elif product_type == ProductType.GROUPED:
                    # Process entire sheet as one grouped product
                    try:
                        product_data = import_service.parse_grouped_product(df, shop_id)
                        product = import_service.create_product(product_data)
                        results['successful'] += 1
                        results['imported_products'].append({
                            'product_id': product.id,
                            'name': product.name,
                            'sku': product.sku,
                            'type': 'grouped',
                            'sheet': sheet_name,
                            'grouped_items': len(product_data.get('grouped_products', []))
                        })
                    except Exception as e:
                        results['failed'] += 1
                        error_msg = f"Sheet '{sheet_name}': {str(e)}"
                        results['errors'].append(error_msg)
                        
            except Exception as e:
                results['failed'] += 1
                error_msg = f"Sheet '{sheet_name}': {str(e)}"
                results['errors'].append(error_msg)
        
        # Update import history with final results
        import_service.update_import_history(
            status="completed",
            errors=results['errors'],
            imported_products=results['imported_products']
        )
        
        # Prepare response
        message = f"Import completed: {results['successful']} successful, {results['failed']} failed"
        
        return api_response(200, message, {
            'import_id': import_history.id,
            'successful': results['successful'],
            'failed': results['failed'],
            'errors': results['errors'][:10]  # Return first 10 errors only
        })
        
    except Exception as e:
        # Update import history with error
        if import_history:
            import_history.status = "failed"
            import_history.import_errors = [f"Import failed: {str(e)}"]
            session.add(import_history)
            session.commit()
        
        return api_response(500, f"Import failed: {str(e)}")

@router.get("/import-history")
def get_import_history(
    session: GetSession,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user=requirePermission("product_view", "shop_admin"),
):
    """
    Get product import history with pagination
    """
    try:
        # Get shop ID from user - with safe handling
        try:
            shop_id = get_user_shop_id(user)
        except ValueError as e:
            return api_response(400, str(e))
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get total count
        total_count_query = select(func.count(ProductImportHistory.id)).where(
            ProductImportHistory.shop_id == shop_id
        )
        total_count = session.exec(total_count_query).first()
        
        # Get paginated results
        import_history = session.exec(
            select(ProductImportHistory)
            .where(ProductImportHistory.shop_id == shop_id)
            .order_by(desc(ProductImportHistory.created_at))
            .offset(offset)
            .limit(limit)
        ).all()
        
        # Format response
        history_data = []
        for record in import_history:
            history_data.append({
                'id': record.id,
                'filename': record.original_filename,
                'file_size': record.file_size,
                'total_records': record.total_records,
                'successful_records': record.successful_records,
                'failed_records': record.failed_records,
                'status': record.status,
                'imported_by': record.imported_by,
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'completed_at': record.completed_at.isoformat() if record.completed_at else None,
                'imported_products': record.imported_products or [],
                'errors_count': len(record.import_errors or [])
            })
        
        return api_response(200, "Import history retrieved", history_data)
        
    except Exception as e:
        return api_response(500, f"Failed to retrieve import history: {str(e)}")

@router.get("/import-history/{import_id}")
def get_import_history_detail(
    import_id: int,
    session: GetSession,
    user=requirePermission("product_view", "shop_admin"),
):
    """
    Get detailed information about a specific import
    """
    try:
        # Get shop ID from user - with safe handling
        try:
            shop_id = get_user_shop_id(user)
        except ValueError as e:
            return api_response(400, str(e))
        
        # Get import history record
        import_history = session.get(ProductImportHistory, import_id)
        raiseExceptions((import_history, 404, "Import record not found"))
        
        # Check if user has access to this import
        if import_history.shop_id != shop_id:
            return api_response(403, "Access denied")
        
        # Get detailed product information
        imported_products_details = []
        for product_info in (import_history.imported_products or []):
            product = session.get(Product, product_info.get('product_id'))
            if product:
                imported_products_details.append({
                    'id': product.id,
                    'name': product.name,
                    'sku': product.sku,
                    'price': product.price,
                    'quantity': product.quantity,
                    'status': product.status,
                    'type': product_info.get('type'),
                    'sheet': product_info.get('sheet'),
                    'row': product_info.get('row')
                })
        
        response_data = {
            'id': import_history.id,
            'filename': import_history.original_filename,
            'file_size': import_history.file_size,
            'total_records': import_history.total_records,
            'successful_records': import_history.successful_records,
            'failed_records': import_history.failed_records,
            'status': import_history.status,
            'imported_by': import_history.imported_by,
            'created_at': import_history.created_at.isoformat() if import_history.created_at else None,
            'completed_at': import_history.completed_at.isoformat() if import_history.completed_at else None,
            'imported_products': imported_products_details,
            'errors': import_history.import_errors or []
        }
        
        return api_response(200, "Import details retrieved", response_data)
        
    except Exception as e:
        return api_response(500, f"Failed to retrieve import details: {str(e)}")

@router.delete("/import-history/{import_id}")
def delete_import_history(
    import_id: int,
    session: GetSession,
    user=requirePermission("product_delete", "shop_admin"),
):
    """
    Delete import history record
    """
    try:
        # Get shop ID from user - with safe handling
        try:
            shop_id = get_user_shop_id(user)
        except ValueError as e:
            return api_response(400, str(e))
        
        # Get import history record
        import_history = session.get(ProductImportHistory, import_id)
        raiseExceptions((import_history, 404, "Import record not found"))
        
        # Check if user has access to this import
        if import_history.shop_id != shop_id:
            return api_response(403, "Access denied")
        
        # Delete record
        session.delete(import_history)
        session.commit()
        
        return api_response(200, "Import history record deleted")
        
    except Exception as e:
        return api_response(500, f"Failed to delete import history: {str(e)}")

@router.get("/import-template")
def download_import_template(
    session: GetSession,
    user=requirePermission("product_create", "shop_admin"),
):
    """
    Download Excel template for product import
    """
    try:
        # Create sample data for template
        sample_data = {
            'Simple_Products': [
                {
                    'name': 'Sample Simple Product 1',
                    'description': 'This is a sample simple product',
                    'price': 29.99,
                    'sale_price': 24.99,
                    'purchase_price': 15.00,
                    'quantity': 100,
                    'weight': 0.5,
                    'category': 'Electronics',
                    'manufacturer': 'TechCorp',
                    'sku': 'SK-SIMPLE-001',
                    'bar_code': '1234567890123',
                    'unit': 'pcs',
                    'tags': 'electronics,gadget,tech'
                }
            ],
            'Variable_Products': [
                {
                    'name': 'Sample T-Shirt',
                    'description': 'A sample variable product with size and color options',
                    'category': 'Clothing',
                    'manufacturer': 'FashionCo',
                    'attribute_size': 'Small',
                    'attribute_color': 'Red',
                    'price': 19.99,
                    'sale_price': 17.99,
                    'purchase_price': 8.00,
                    'quantity': 25,
                    'sku': 'SK-TSHIRT-S-RED',
                    'bar_code': '1234567890125'
                }
            ],
            'Grouped_Products': [
                {
                    'name': 'Sample Computer Bundle',
                    'description': 'A complete computer setup bundle',
                    'category': 'Electronics',
                    'manufacturer': 'TechBundle',
                    'grouped_product_id': 'SK-SIMPLE-001',
                    'quantity': 1
                }
            ]
        }
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, data in sample_data.items():
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        
        # Return file response
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=product_import_template.xlsx"}
        )
        
    except Exception as e:
        return api_response(500, f"Failed to generate template: {str(e)}")