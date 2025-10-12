# scripts/generate_sample_excel.py
import pandas as pd

def generate_sample_excel():
    """Generate a detailed sample Excel file for product import"""
    
    # Sample data for different product types
    sample_data = {
        'Simple_Products': [
            {
                'name': 'Wireless Bluetooth Headphones',
                'description': 'High-quality wireless headphones with noise cancellation',
                'price': 79.99,
                'sale_price': 69.99,
                'purchase_price': 35.00,
                'quantity': 150,
                'weight': 0.3,
                'category': 'Electronics',
                'manufacturer': 'AudioTech',
                'sku': 'SK-HEADPHONE-001',
                'bar_code': '1234567890128',
                'unit': 'pcs',
                'tags': 'electronics,audio,wireless,bluetooth',
                'warranty': '1 year manufacturer warranty',
                'shipping_info': 'Free shipping',
                'meta_title': 'Wireless Bluetooth Headphones - Best Audio Quality',
                'meta_description': 'Premium wireless headphones with noise cancellation technology'
            },
            {
                'name': 'Stainless Steel Water Bottle',
                'description': 'Eco-friendly stainless steel water bottle, keeps drinks cold for 24 hours',
                'price': 24.99,
                'sale_price': 19.99,
                'purchase_price': 8.50,
                'quantity': 200,
                'weight': 0.4,
                'category': 'Home & Kitchen',
                'manufacturer': 'EcoLiving',
                'sku': 'SK-BOTTLE-001',
                'bar_code': '1234567890129',
                'unit': 'pcs',
                'tags': 'kitchen,eco-friendly,stainless-steel',
                'warranty': 'Lifetime warranty',
                'shipping_info': 'Free shipping on orders over $50',
                'meta_title': 'Stainless Steel Water Bottle - Eco Friendly',
                'meta_description': 'Keep your drinks cold with our premium stainless steel water bottle'
            }
        ],
        'Variable_Products': [
            {
                'name': 'Premium Running Shoes',
                'description': 'High-performance running shoes for all terrains',
                'category': 'Sports & Outdoors',
                'manufacturer': 'RunFast',
                'attribute_size': 'US 7',
                'attribute_color': 'Black',
                'price': 129.99,
                'sale_price': 119.99,
                'purchase_price': 65.00,
                'quantity': 25,
                'sku': 'SK-SHOES-7-BLACK',
                'bar_code': '1234567890130'
            },
            {
                'name': 'Premium Running Shoes',
                'description': 'High-performance running shoes for all terrains',
                'category': 'Sports & Outdoors',
                'manufacturer': 'RunFast',
                'attribute_size': 'US 7',
                'attribute_color': 'White',
                'price': 129.99,
                'sale_price': 119.99,
                'purchase_price': 65.00,
                'quantity': 20,
                'sku': 'SK-SHOES-7-WHITE',
                'bar_code': '1234567890131'
            },
            {
                'name': 'Premium Running Shoes',
                'description': 'High-performance running shoes for all terrains',
                'category': 'Sports & Outdoors',
                'manufacturer': 'RunFast',
                'attribute_size': 'US 8',
                'attribute_color': 'Black',
                'price': 129.99,
                'sale_price': 119.99,
                'purchase_price': 65.00,
                'quantity': 30,
                'sku': 'SK-SHOES-8-BLACK',
                'bar_code': '1234567890132'
            },
            {
                'name': 'Premium Running Shoes',
                'description': 'High-performance running shoes for all terrains',
                'category': 'Sports & Outdoors',
                'manufacturer': 'RunFast',
                'attribute_size': 'US 8',
                'attribute_color': 'Blue',
                'price': 129.99,
                'sale_price': 119.99,
                'purchase_price': 65.00,
                'quantity': 15,
                'sku': 'SK-SHOES-8-BLUE',
                'bar_code': '1234567890133'
            }
        ],
        'Grouped_Products': [
            {
                'name': 'Office Desk Setup Bundle',
                'description': 'Complete office desk setup including monitor, keyboard, and mouse',
                'category': 'Electronics',
                'manufacturer': 'OfficePro',
                'grouped_product_id': 'SK-HEADPHONE-001',
                'quantity': 1
            },
            {
                'name': 'Office Desk Setup Bundle',
                'description': 'Complete office desk setup including monitor, keyboard, and mouse',
                'category': 'Electronics',
                'manufacturer': 'OfficePro',
                'grouped_product_id': 'SK-BOTTLE-001',
                'quantity': 1
            }
        ],
        'Instructions': [
            {
                'Sheet_Name': 'Description',
                'Instructions': 'Fill data according to product type:',
                'Examples': ''
            },
            {
                'Sheet_Name': 'Simple_Products',
                'Instructions': 'Each row = One product. Fill all columns',
                'Examples': 'See sample data above'
            },
            {
                'Sheet_Name': 'Variable_Products', 
                'Instructions': 'Multiple rows for same product with different attributes',
                'Examples': 'Use attribute_ columns for variations'
            },
            {
                'Sheet_Name': 'Grouped_Products',
                'Instructions': 'Reference existing products by SKU or ID',
                'Examples': 'grouped_product_id must exist in system'
            }
        ]
    }
    
    # Create Excel file
    with pd.ExcelWriter('product_import_sample.xlsx', engine='openpyxl') as writer:
        for sheet_name, data in sample_data.items():
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print("Sample Excel file generated: product_import_sample.xlsx")

if __name__ == "__main__":
    generate_sample_excel()