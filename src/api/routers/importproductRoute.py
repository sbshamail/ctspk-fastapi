# src/api/routes/product_import.py
import pandas as pd
import io
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, Query, HTTPException
from sqlmodel import Session, select, desc, func, or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from src.api.core.dependencies import GetSession, requirePermission
from src.api.core.response import api_response, raiseExceptions
from src.api.models.product_model.productsModel import (
    Product, ProductType, ProductStatus,
    ProductAttribute, VariationData
)
from src.api.models.product_model.importHistoryModel import ProductImportHistory
from src.api.models.product_model.productPurchaseModel import (
    ProductPurchase, PurchaseType, TransactionType
)
from src.api.models.category_model.categoryModel import Category
from src.api.models.manufacturer_model.manufacturerModel import Manufacturer
from src.api.models.product_model.variationOptionModel import VariationOption
from src.api.models.shop_model.shopsModel import Shop
from src.api.core.utility import uniqueSlugify
from src.api.core.sku_generator import generate_unique_sku
from src.api.core.transaction_logger import TransactionLogger

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
        self.categories_map.update({str(cat.id): cat.id for cat in categories})
        
        # Load manufacturers
        manufacturers = self.session.exec(select(Manufacturer)).all()
        self.manufacturers_map = {mfg.name.lower(): mfg.id for mfg in manufacturers}
        self.manufacturers_map.update({str(mfg.id): mfg.id for mfg in manufacturers})
        
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
    
    def validate_user_shop_access(self, user: dict, shop_identifier: str) -> int:
        """Validate that user has access to the specified shop"""
        if not shop_identifier:
            raise ValueError("Shop identifier (id, name, or slug) is required")
            
        user_shops = user.get("shops", [])
        if not user_shops:
            raise ValueError("User is not associated with any shop")
        
        # Try to find shop by ID, name, or slug
        shop = None
        for user_shop in user_shops:
            if (str(user_shop.get("id")) == str(shop_identifier) or 
                user_shop.get("name", "").lower() == shop_identifier.lower() or
                user_shop.get("slug", "").lower() == shop_identifier.lower()):
                shop = user_shop
                break
        
        if not shop:
            raise ValueError(f"User doesn't have access to shop: {shop_identifier}")
            
        return shop.get("id")
    
    def get_category_id(self, category_name: str) -> int:
        """Get category ID by name - only use existing categories"""
        if not category_name:
            raise ValueError("Category name is required")
            
        category_key = category_name.strip().lower()
        
        if category_key in self.categories_map:
            return self.categories_map[category_key]
        else:
            # Try to find by ID
            try:
                category_id = int(category_name)
                if str(category_id) in self.categories_map:
                    return category_id
            except ValueError:
                pass
                
            raise ValueError(f"Category '{category_name}' not found in database. Please create category first.")
    
    def get_manufacturer_id(self, manufacturer_name: str) -> Optional[int]:
        """Get manufacturer ID by name - only use existing manufacturers"""
        if not manufacturer_name:
            return None
            
        manufacturer_key = manufacturer_name.strip().lower()
        
        if manufacturer_key in self.manufacturers_map:
            return self.manufacturers_map[manufacturer_key]
        else:
            # Try to find by ID
            try:
                manufacturer_id = int(manufacturer_name)
                if str(manufacturer_id) in self.manufacturers_map:
                    return manufacturer_id
            except ValueError:
                pass
                
            raise ValueError(f"Manufacturer '{manufacturer_name}' not found in database. Please create manufacturer first.")

    def create_purchase_record(self, product_id: int, quantity: int, purchase_price: float, 
                             shop_id: int, added_by: int, notes: str = None, product_name: str = None):
        """Create purchase record for imported products"""
        try:
            # Get current stock before addition
            product = self.session.get(Product, product_id)
            previous_stock = product.quantity if product else 0
            new_stock = previous_stock + quantity
            
            # Get import history for reference
            import_history = None
            if self.import_history_id:
                import_history = self.session.get(ProductImportHistory, self.import_history_id)
            
            purchase = ProductPurchase(
                product_id=product_id,
                quantity=quantity,
                purchase_price=purchase_price,
                shop_id=shop_id,
                purchase_type=PurchaseType.DEBIT,
                transaction_type=TransactionType.STOCK_ADDITION,
                reference_number=f"IMP-{uuid.uuid4().hex[:8].upper()}",
                supplier_name="Import System",
                notes=notes or f"Initial stock added for product: {product_name or 'Unknown'} via Excel import",
                added_by=added_by,
                previous_stock=previous_stock,
                new_stock=new_stock,
                transaction_details={
                    "import_method": "excel_import",
                    "original_filename": import_history.original_filename if import_history else "Unknown",
                    "import_id": self.import_history_id,
                    "product_name": product_name
                }
            )
            
            self.session.add(purchase)
            self.session.commit()
            
            # Update product's total purchased quantity
            if product:
                product.total_purchased_quantity += quantity
                self.session.add(product)
                self.session.commit()
                
            return purchase
            
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error creating purchase record: {str(e)}")

    def parse_simple_product(self, row: pd.Series, shop_id: int) -> Dict[str, Any]:
        """Parse simple product data from Excel row"""
        try:
            # Required fields
            name = str(row['name']).strip()
            if not name:
                raise ValueError("Product name is required")
                
            price = float(row['price']) if pd.notna(row['price']) else 0
            category_name = str(row['category']).strip()
            
            # Validate category exists
            category_id = self.get_category_id(category_name)
            
            # Validate manufacturer exists if provided
            manufacturer_id = None
            if pd.notna(row.get('manufacturer')):
                manufacturer_id = self.get_manufacturer_id(str(row.get('manufacturer', '')).strip())
            
            # Optional fields with defaults
            description = str(row.get('description', '')).strip()
            sku = str(row.get('sku', '')).strip() or generate_unique_sku(self.session)
            bar_code = str(row.get('bar_code', '')).strip()
            quantity = int(row.get('quantity', 0)) if pd.notna(row.get('quantity')) else 0
            weight = float(row.get('weight', 0)) if pd.notna(row.get('weight')) else None
            sale_price = float(row.get('sale_price')) if pd.notna(row.get('sale_price')) else None
            purchase_price = float(row.get('purchase_price', 0)) if pd.notna(row.get('purchase_price')) else 0
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
            
            manufacturer_id = None
            if pd.notna(main_row.get('manufacturer')):
                manufacturer_id = self.get_manufacturer_id(str(main_row.get('manufacturer', '')).strip())
            
            # Parse attributes
            attributes = self.parse_attributes(df)
            
            # Parse variations
            variations = self.parse_variations(df, name)
            
            # Calculate min/max prices from variations
            prices = [var.price for var in variations]
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            
            # Calculate total quantity from variations
            total_quantity = sum(var.quantity for var in variations)
            
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
                'quantity': total_quantity,
                'purchase_price': 0,  # Will be calculated from variations
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
                purchase_price = float(row.get('purchase_price', 0)) if pd.notna(row.get('purchase_price')) else 0
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
    
     
    def create_product(self, product_data: Dict[str, Any], added_by: int) -> Product:
        """Create product in database with purchase tracking"""
        try:
            # Create main product
            product = Product(
                name=product_data['name'],
                description=product_data.get('description', ''),
                price=product_data.get('price', 0),
                sale_price=product_data.get('sale_price'),
                purchase_price=product_data.get('purchase_price', 0),
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
                if 'grouped_products_config' in product_data:
                    product.grouped_products_config = product_data['grouped_products_config'].dict()
            
            self.session.add(product)
            self.session.commit()
            self.session.refresh(product)

            # Log product creation with TransactionLogger
            logger = TransactionLogger(self.session)
            logger.log_product_creation(
                product=product,
                user_id=added_by,
                notes=f"Product created via import: {product_data['name']}"
            )

            # Create purchase record for the initial quantity if it's a simple product
            if (product_data['product_type'] == ProductType.SIMPLE and
                product_data.get('quantity', 0) > 0 and
                product_data.get('purchase_price', 0) > 0):

                purchase_notes = f"Initial stock added for new product: {product_data['name']} via import"
                self.create_purchase_record(
                    product_id=product.id,
                    quantity=product_data['quantity'],
                    purchase_price=product_data['purchase_price'],
                    shop_id=product_data['shop_id'],
                    added_by=added_by,
                    notes=purchase_notes,
                    product_name=product_data['name']
                )

                # Log stock addition with TransactionLogger
                logger.log_stock_addition(
                    product=product,
                    quantity=product_data['quantity'],
                    purchase_price=product_data['purchase_price'],
                    user_id=added_by,
                    notes=purchase_notes,
                    previous_quantity=0,
                    new_quantity=product_data['quantity']
                )
            
            # Create variations for variable products
            if product_data['product_type'] == ProductType.VARIABLE and 'variations' in product_data:
                self.create_variations(product.id, product_data['variations'], added_by, product_data['shop_id'])
            
            return product
            
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error creating product: {str(e)}")
    
    def create_variations(self, product_id: int, variations: List[VariationData], added_by: int, shop_id: int):
        """Create variation options for variable product with purchase tracking"""
        logger = TransactionLogger(self.session)
        product = self.session.get(Product, product_id)

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
                self.session.flush()  # Flush to get variation ID

                # Create purchase record for variation stock
                if variation.quantity > 0 and variation.purchase_price > 0:
                    purchase_notes = f"Initial stock added for variation: {title} via import"
                    self.create_purchase_record(
                        product_id=product_id,
                        quantity=variation.quantity,
                        purchase_price=variation.purchase_price,
                        shop_id=shop_id,
                        added_by=added_by,
                        notes=purchase_notes,
                        product_name=title
                    )

                    # Log stock addition with TransactionLogger for variation
                    if product:
                        logger.log_stock_addition(
                            product=product,
                            quantity=variation.quantity,
                            purchase_price=variation.purchase_price,
                            user_id=added_by,
                            notes=purchase_notes,
                            variation_option_id=variation_option.id,
                            previous_quantity=0,
                            new_quantity=variation.quantity
                        )

            except Exception as e:
                raise ValueError(f"Error creating variation: {str(e)}")

        self.session.commit()

def get_user_shops(user: dict) -> List[Dict]:
    """Get user's shops"""
    return user.get("shops", [])

def get_user_shop_ids(user: dict) -> List[int]:
    """Get user's shop IDs"""
    shops = get_user_shops(user)
    return [shop.get("id") for shop in shops if shop.get("id")]

@router.post("/import-excel")
def import_products_from_excel(
    session: GetSession,
    file: UploadFile = File(...),
    user=requirePermission("product_create", "shop_admin"),
):
    """
    Import products from Excel file with shop validation and purchase tracking
    Only imports products if category and manufacturer exist in database
    """
    import_history = None
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            return api_response(400, "Only Excel files (.xlsx, .xls) are supported")
        
        # Read Excel file first to get shop information
        contents = file.file.read()
        excel_file = io.BytesIO(contents)
        
        # Initialize import service
        import_service = ProductImportService(session)
        import_service.load_reference_data()
        
        # Read first sheet to get shop info
        xl = pd.ExcelFile(excel_file)
        first_sheet_name = xl.sheet_names[0]
        df = pd.read_excel(excel_file, sheet_name=first_sheet_name)
        
        # Check if shop column exists
        if 'shop_id' not in df.columns and 'shop_name' not in df.columns and 'shop_slug' not in df.columns:
            return api_response(400, "Excel file must contain 'shop_id', 'shop_name', or 'shop_slug' column")
        
        # Get shop identifier from first row
        first_row = df.iloc[0]
        shop_identifier = None
        if 'shop_id' in df.columns and pd.notna(first_row.get('shop_id')):
            shop_identifier = str(first_row['shop_id']).strip()
        elif 'shop_name' in df.columns and pd.notna(first_row.get('shop_name')):
            shop_identifier = str(first_row['shop_name']).strip()
        elif 'shop_slug' in df.columns and pd.notna(first_row.get('shop_slug')):
            shop_identifier = str(first_row['shop_slug']).strip()
        
        if not shop_identifier:
            return api_response(400, "Shop identifier not found in Excel file")
        
        # Validate user has access to this shop
        try:
            shop_id = import_service.validate_user_shop_access(user, shop_identifier)
        except ValueError as e:
            return api_response(400, str(e))
        
        # Create import history record
        import_history = ProductImportHistory(
            filename=f"import_{uuid.uuid4().hex[:8]}.xlsx",
            original_filename=file.filename,
            file_size=len(contents),
            shop_id=shop_id,
            imported_by=user.get("id"),
            status="processing"
        )
        session.add(import_history)
        session.commit()
        session.refresh(import_history)
        
        # Update service with history ID
        import_service.import_history_id = import_history.id
        
        # Process each sheet
        results = {
            'successful': 0,
            'failed': 0,
            'errors': [],
            'imported_products': []
        }
        
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
                else:
                    product_type = ProductType.SIMPLE
                
                # Process based on product type
                if product_type == ProductType.SIMPLE:
                    for idx, row in df.iterrows():
                        try:
                            # Validate shop access for each row if shop info is provided
                            row_shop_identifier = None
                            if 'shop_id' in df.columns and pd.notna(row.get('shop_id')):
                                row_shop_identifier = str(row['shop_id']).strip()
                            elif 'shop_name' in df.columns and pd.notna(row.get('shop_name')):
                                row_shop_identifier = str(row['shop_name']).strip()
                            elif 'shop_slug' in df.columns and pd.notna(row.get('shop_slug')):
                                row_shop_identifier = str(row['shop_slug']).strip()
                            
                            if row_shop_identifier:
                                row_shop_id = import_service.validate_user_shop_access(user, row_shop_identifier)
                            else:
                                row_shop_id = shop_id
                            
                            product_data = import_service.parse_simple_product(row, row_shop_id)
                            product = import_service.create_product(product_data, user.get("id"))
                            results['successful'] += 1
                            results['imported_products'].append({
                                'product_id': product.id,
                                'name': product.name,
                                'sku': product.sku,
                                'type': 'simple',
                                'sheet': sheet_name,
                                'row': idx + 2,
                                'quantity': product.quantity,
                                'purchase_price': product.purchase_price
                            })
                        except Exception as e:
                            results['failed'] += 1
                            error_msg = f"Sheet '{sheet_name}', Row {idx + 2}: {str(e)}"
                            results['errors'].append(error_msg)
                
                elif product_type == ProductType.VARIABLE:
                    try:
                        product_data = import_service.parse_variable_product(df, shop_id)
                        product = import_service.create_product(product_data, user.get("id"))
                        results['successful'] += 1
                        results['imported_products'].append({
                            'product_id': product.id,
                            'name': product.name,
                            'sku': product.sku,
                            'type': 'variable',
                            'sheet': sheet_name,
                            'variations': len(product_data.get('variations', [])),
                            'total_quantity': product.quantity
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
        # Get user's shop IDs
        user_shop_ids = get_user_shop_ids(user)
        if not user_shop_ids:
            return api_response(400, "User is not associated with any shop")
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get total count
        total_count_query = select(func.count(ProductImportHistory.id)).where(
            ProductImportHistory.shop_id.in_(user_shop_ids)
        )
        total_count = session.exec(total_count_query).first()
        
        # Get paginated results
        import_history = session.exec(
            select(ProductImportHistory)
            .where(ProductImportHistory.shop_id.in_(user_shop_ids))
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
        
        return api_response(200, "Import history retrieved", history_data,total_count)
        #  {
        #     'data': history_data,
        #     'pagination': {
        #         'page': page,
        #         'limit': limit,
        #         'total': total_count,
        #         'pages': (total_count + limit - 1) // limit
        #     }
        # } 
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
        # Get user's shop IDs
        user_shop_ids = get_user_shop_ids(user)
        if not user_shop_ids:
            return api_response(400, "User is not associated with any shop")
        
        # Get import history record
        import_history = session.get(ProductImportHistory, import_id)
        if not import_history:
            return api_response(404, "Import record not found")
        
        # Check if user has access to this import
        if import_history.shop_id not in user_shop_ids:
            return api_response(403, "Access denied")
        
        # Get detailed product information
        imported_products_details = []
        for product_info in (import_history.imported_products or []):
            product = session.get(Product, product_info.get('product_id'))
            if product:
                # Get category name
                category = session.get(Category, product.category_id)
                category_name = category.name if category else "Unknown"
                
                # Get manufacturer name
                manufacturer_name = "Unknown"
                if product.manufacturer_id:
                    manufacturer = session.get(Manufacturer, product.manufacturer_id)
                    manufacturer_name = manufacturer.name if manufacturer else "Unknown"
                
                # Get purchase records for this product
                purchase_records = session.exec(
                    select(ProductPurchase).where(ProductPurchase.product_id == product.id)
                ).all()
                
                imported_products_details.append({
                    'id': product.id,
                    'name': product.name,
                    'sku': product.sku,
                    'price': product.price,
                    'quantity': product.quantity,
                    'status': product.status,
                    'category': category_name,
                    'manufacturer': manufacturer_name,
                    'type': product_info.get('type'),
                    'sheet': product_info.get('sheet'),
                    'row': product_info.get('row'),
                    'total_purchased_quantity': product.total_purchased_quantity,
                    'total_sold_quantity': product.total_sold_quantity,
                    'purchase_records_count': len(purchase_records)
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

    except HTTPException:
        raise
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
        # Get user's shop IDs
        user_shop_ids = get_user_shop_ids(user)
        if not user_shop_ids:
            return api_response(400, "User is not associated with any shop")
        
        # Get import history record
        import_history = session.get(ProductImportHistory, import_id)
        if not import_history:
            return api_response(404, "Import record not found")
        
        # Check if user has access to this import
        if import_history.shop_id not in user_shop_ids:
            return api_response(403, "Access denied")
        
        # Delete record
        session.delete(import_history)
        session.commit()
        
        return api_response(200, "Import history record deleted")
        
    except Exception as e:
        session.rollback()
        return api_response(500, f"Failed to delete import history: {str(e)}")

@router.get("/export-excel")
def export_products_to_excel(
    session: GetSession,
    shop_id: Optional[int] = Query(None, description="Filter by shop ID"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    manufacturer_id: Optional[int] = Query(None, description="Filter by manufacturer ID"),
    low_stock: Optional[bool] = Query(None, description="Filter low stock products"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user=requirePermission("product_view", "shop_admin"),
):
    """
    Export products to Excel with filters including purchase and sales data
    """
    try:
        # Build query based on user's shops and filters
        user_shop_ids = get_user_shop_ids(user)
        
        if not user_shop_ids:
            return api_response(400, "User is not associated with any shop")
        
        query = select(Product).where(Product.shop_id.in_(user_shop_ids))
        
        # Apply filters
        if shop_id:
            if shop_id not in user_shop_ids:
                return api_response(403, "Access denied to specified shop")
            query = query.where(Product.shop_id == shop_id)
        
        if category_id:
            query = query.where(Product.category_id == category_id)
            
        if manufacturer_id:
            query = query.where(Product.manufacturer_id == manufacturer_id)
            
        if low_stock:
            query = query.where(Product.quantity <= 10)  # Define low stock threshold
            
        if start_date:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.where(Product.created_at >= start_datetime)
            
        if end_date:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            query = query.where(Product.created_at <= end_datetime)
        
        # Execute query
        products = session.exec(query).all()
        
        if not products:
            return api_response(404, "No products found matching the criteria")
        
        # Prepare data for Excel
        product_data = []
        for product in products:
            # Get shop name
            shop = session.get(Shop, product.shop_id)
            shop_name = shop.name if shop else "Unknown"
            
            # Get category name
            category = session.get(Category, product.category_id)
            category_name = category.name if category else "Unknown"
            
            # Get manufacturer name
            manufacturer_name = "Unknown"
            if product.manufacturer_id:
                manufacturer = session.get(Manufacturer, product.manufacturer_id)
                manufacturer_name = manufacturer.name if manufacturer else "Unknown"
            
            # Calculate current stock value
            current_stock_value = product.purchase_price * product.quantity if product.purchase_price else 0
            
            product_data.append({
                'ID': product.id,
                'Name': product.name,
                'Description': product.description or '',
                'SKU': product.sku,
                'Barcode': product.bar_code or '',
                'Price': product.price,
                'Sale Price': product.sale_price or '',
                'Purchase Price': product.purchase_price or '',
                'Current Quantity': product.quantity,
                'Total Purchased': product.total_purchased_quantity,
                'Total Sold': product.total_sold_quantity,
                'Weight': product.weight or '',
                'Category': category_name,
                'Manufacturer': manufacturer_name,
                'Shop': shop_name,
                'Type': product.product_type.value,
                'Status': product.status.value,
                'Unit': product.unit,
                'Tags': ', '.join(product.tags) if product.tags else '',
                'Created At': product.created_at.strftime("%Y-%m-%d %H:%M:%S") if product.created_at else '',
                'Min Price': product.min_price,
                'Max Price': product.max_price,
                'Current Stock Value': current_stock_value,
                'In Stock': 'Yes' if product.in_stock else 'No'
            })
        
        # Create Excel file
        df = pd.DataFrame(product_data)
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Products']
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)
        
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"products_export_{timestamp}.xlsx"
        
        # Return file response
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        return api_response(500, f"Failed to export products: {str(e)}")

@router.get("/user-shops")
def get_user_shops_list(
    session: GetSession,
    user=requirePermission("product_view", "shop_admin"),
):
    """
    Get list of shops associated with the user
    """
    try:
        user_shops = get_user_shops(user)
        return api_response(200, "User shops retrieved", user_shops, len(user_shops))
    except Exception as e:
        return api_response(500, f"Failed to retrieve user shops: {str(e)}")

@router.get("/import-template")
def download_import_template(
    session: GetSession,
    user=requirePermission("product_create", "shop_admin"),
):
    """
    Download Excel template for product import with shop selection and purchase tracking
    """
    try:
        # Get user's shops for the template
        user_shops = get_user_shops(user)
        
        if not user_shops:
            return api_response(400, "User is not associated with any shop")
        
        # Create sample data for template
        sample_data = {
            'Simple_Products': [
                {
                    'shop_id': user_shops[0].get("id"),
                    'shop_name': user_shops[0].get("name"),
                    'shop_slug': user_shops[0].get("slug"),
                    'name': 'Sample Simple Product 1',
                    'description': 'This is a sample simple product',
                    'price': 29.99,
                    'sale_price': 24.99,
                    'purchase_price': 15.00,  # Required for purchase tracking
                    'quantity': 100,
                    'weight': 0.5,
                    'category': 'Electronics',  # Must exist in database
                    'manufacturer': 'TechCorp',  # Must exist in database
                    'sku': 'SK-SIMPLE-001',
                    'bar_code': '1234567890123',
                    'unit': 'pcs',
                    'tags': 'electronics,gadget,tech'
                }
            ],
            'Variable_Products': [
                {
                    'shop_id': user_shops[0].get("id"),
                    'name': 'Sample T-Shirt',
                    'description': 'A sample variable product with size and color options',
                    'category': 'Clothing',  # Must exist in database
                    'manufacturer': 'FashionCo',  # Must exist in database
                    'attribute_size': 'Small',
                    'attribute_color': 'Red',
                    'price': 19.99,
                    'sale_price': 17.99,
                    'purchase_price': 8.00,  # Purchase price for this variation
                    'quantity': 25,
                    'sku': 'SK-TSHIRT-S-RED',
                    'bar_code': '1234567890125'
                },
                {
                    'shop_id': user_shops[0].get("id"),
                    'name': 'Sample T-Shirt',
                    'description': 'A sample variable product with size and color options',
                    'category': 'Clothing',
                    'manufacturer': 'FashionCo',
                    'attribute_size': 'Medium',
                    'attribute_color': 'Blue',
                    'price': 21.99,
                    'sale_price': 19.99,
                    'purchase_price': 9.00,
                    'quantity': 30,
                    'sku': 'SK-TSHIRT-M-BLUE',
                    'bar_code': '1234567890126'
                }
            ]
        }
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, data in sample_data.items():
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(df.columns):
                    max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 30)
        
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