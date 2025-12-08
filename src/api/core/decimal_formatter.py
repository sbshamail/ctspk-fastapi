# src/api/core/decimal_formatter.py
"""
Utility for formatting decimal/float values to always show 2 decimal places
Applies only to monetary fields, not dimensions/measurements
"""
from typing import Optional, Union, Any, Dict
from decimal import Decimal, ROUND_HALF_UP


def format_decimal(value: Optional[Union[float, Decimal, int]]) -> float:
    """
    Format a numeric value to always have 2 decimal places

    Args:
        value: The numeric value to format (float, Decimal, int, or None)

    Returns:
        float: Formatted value with 2 decimal places, or 0.00 if None/0

    Examples:
        format_decimal(10) -> 10.00
        format_decimal(10.5) -> 10.50
        format_decimal(10.567) -> 10.57
        format_decimal(None) -> 0.00
        format_decimal(0) -> 0.00
    """
    if value is None or value == 0:
        return 0.00

    # Convert to Decimal for precise rounding
    if isinstance(value, (int, float)):
        decimal_value = Decimal(str(value))
    elif isinstance(value, Decimal):
        decimal_value = value
    else:
        return 0.00

    # Round to 2 decimal places
    rounded = decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Convert back to float with 2 decimal places
    return float(rounded)


# Complete list of monetary fields across all tables
# These will be formatted to 2 decimal places
MONETARY_FIELDS = {
    # Price fields
    'price', 'sale_price', 'purchase_price', 'min_price', 'max_price',
    'unit_price', 'unit_purchase_price',

    # Amount fields
    'amount', 'paid_total', 'cancelled_amount', 'total_amount',
    'order_amount', 'refund_amount', 'approved_amount', 'total_cost',
    'net_amount', 'balance_after',

    # Discount fields
    'discount', 'coupon_discount', 'item_discount', 'discount_amount',

    # Tax and Fee fields
    'sales_tax', 'delivery_fee', 'item_tax', 'tax_amount',
    'shipping_cost', 'restocking_fee',

    # Subtotal and Total fields
    'subtotal', 'total',

    # Commission and Earnings
    'admin_commission_amount', 'admin_commission', 'shop_earning',
}


def format_monetary_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format all monetary fields in a dictionary to 2 decimal places
    Used as model_serializer in Pydantic models

    Args:
        data: Dictionary containing model data

    Returns:
        dict: Dictionary with formatted monetary values

    Example usage in Pydantic model:
        @model_serializer
        def serialize_model(self):
            data = {
                'id': self.id,
                'price': self.price,
                'total': self.total,
                ...
            }
            return format_monetary_dict(data)
    """
    formatted = {}

    for key, value in data.items():
        # Format only if field is in monetary list and has a value
        if key in MONETARY_FIELDS and value is not None:
            formatted[key] = format_decimal(value)
        else:
            formatted[key] = value

    return formatted
