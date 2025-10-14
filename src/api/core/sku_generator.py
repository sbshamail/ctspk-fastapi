# src/api/core/sku_generator.py
import random
import string
from sqlmodel import select
from src.api.models.product_model.productsModel import Product
from src.api.models.product_model.variationOptionModel import VariationOption


def generate_unique_sku(session, prefix="SK-", length=9, model=Product, max_attempts=100):
    """
    Generate a unique SKU starting with prefix followed by numbers.
    """
    for attempt in range(max_attempts):
        # Generate random digits
        digits = ''.join(random.choices(string.digits, k=length))
        sku = f"{prefix}{digits}"
        
        # Check if SKU exists in products
        existing_product = session.exec(
            select(model).where(model.sku == sku)
        ).first()
        
        # Check if SKU exists in variations
        existing_variation = session.exec(
            select(VariationOption).where(VariationOption.sku == sku)
        ).first()
        
        if not existing_product and not existing_variation:
            return sku
    
    # If we can't generate a unique SKU after max attempts, raise error
    raise ValueError(f"Failed to generate unique SKU after {max_attempts} attempts")


def generate_sku_for_variation(session, base_sku, variation_suffix=None):
    """
    Generate SKU for variation based on base product SKU.
    """
    if variation_suffix:
        # Use provided suffix
        variation_sku = f"{base_sku}-{variation_suffix}"
    else:
        # Generate unique variation SKU
        variation_sku = generate_unique_sku(
            session, 
            prefix=f"{base_sku}-", 
            length=3,
            model=VariationOption
        )
    
    return variation_sku