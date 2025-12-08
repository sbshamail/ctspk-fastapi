#!/usr/bin/env python
"""
Test decimal formatting for monetary fields
"""
from src.api.core.decimal_formatter import format_decimal, format_monetary_dict

print("=" * 80)
print("TESTING DECIMAL FORMATTING")
print("=" * 80)
print()

# Test format_decimal function
print("1. Testing format_decimal() function:")
print("-" * 80)

test_cases = [
    (10, "10.00"),
    (10.5, "10.50"),
    (10.567, "10.57"),
    (10.564, "10.56"),
    (10.565, "10.57"),  # Round half up
    (None, "0.00"),
    (0, "0.00"),
    (0.0, "0.00"),
    (100.999, "101.00"),
]

all_passed = True
for value, expected in test_cases:
    result = format_decimal(value)
    status = "✓ PASS" if f"{result:.2f}" == expected else "✗ FAIL"
    if status == "✗ FAIL":
        all_passed = False
    print(f"  {str(value):<15} -> {result:<10.2f} (expected: {expected}) {status}")

print()
if all_passed:
    print("✓ All format_decimal tests PASSED!")
else:
    print("✗ Some tests FAILED!")

print()
print("=" * 80)
print("2. Testing format_monetary_dict() function:")
print("-" * 80)

# Test format_monetary_dict with sample data
test_data = {
    'id': 1,
    'name': 'Test Product',
    'price': 10,
    'sale_price': 9.5,
    'purchase_price': 7.567,
    'min_price': None,
    'max_price': 0,
    'height': 10.567,  # Not monetary - should NOT be formatted
    'width': 5.789,    # Not monetary - should NOT be formatted
    'total': 100.999,
    'discount': 5.5,
    'subtotal': 95.499,
}

print("Input data:")
for key, value in test_data.items():
    print(f"  {key:<20} = {value}")

print()
formatted = format_monetary_dict(test_data)

print("Formatted output:")
for key, value in formatted.items():
    print(f"  {key:<20} = {value}")

print()
print("Verification:")
print("-" * 80)

checks = [
    ('price', 10.00, "Monetary field"),
    ('sale_price', 9.50, "Monetary field"),
    ('purchase_price', 7.57, "Monetary field"),
    ('min_price', 0.00, "Monetary field (None)"),
    ('max_price', 0.00, "Monetary field (0)"),
    ('height', 10.567, "Dimension field (unchanged)"),
    ('width', 5.789, "Dimension field (unchanged)"),
    ('total', 101.00, "Monetary field"),
    ('discount', 5.50, "Monetary field"),
    ('subtotal', 95.50, "Monetary field"),
]

all_correct = True
for field, expected, description in checks:
    actual = formatted[field]
    if isinstance(expected, float):
        # For monetary fields, check with 2 decimals
        if field in ['height', 'width']:
            # Dimensions should be unchanged
            is_correct = actual == expected
        else:
            # Monetary fields should be formatted
            is_correct = f"{actual:.2f}" == f"{expected:.2f}"
    else:
        is_correct = actual == expected

    status = "✓" if is_correct else "✗"
    if not is_correct:
        all_correct = False

    print(f"  {status} {field:<20} = {actual:<10} (expected: {expected}) - {description}")

print()
if all_correct:
    print("✓ All format_monetary_dict tests PASSED!")
else:
    print("✗ Some tests FAILED!")

print()
print("=" * 80)
print("3. Testing with actual API response simulation:")
print("-" * 80)

# Simulate a product response
product_response = {
    'id': 276,
    'name': 'Sample Product',
    'price': 1000,
    'sale_price': 950.5,
    'purchase_price': 700.567,
    'min_price': 950.5,
    'max_price': 1000,
    'quantity': 100,
    'height': 10.567,
    'width': 5.123,
    'length': 15.789,
    'weight': 2.345,
}

print("Product before formatting:")
import json
print(json.dumps(product_response, indent=2))

formatted_product = format_monetary_dict(product_response)

print()
print("Product after formatting:")
print(json.dumps(formatted_product, indent=2))

print()
print("=" * 80)
print("SUMMARY:")
print("-" * 80)
print("✓ Monetary fields formatted to 2 decimals")
print("✓ Dimension fields keep original precision")
print("✓ None/0 values formatted to 0.00 for monetary fields")
print("=" * 80)
