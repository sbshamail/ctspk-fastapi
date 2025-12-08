# Float/Double Fields Analysis - All Tables

## Summary

**Tables scanned:** 12
**Tables with numeric fields:** 9

---

## Complete List of Numeric Fields by Table

### 1. ORDERS (9 fields)
| Field Name | Type | Nullable | Format to 2 decimals? |
|------------|------|----------|----------------------|
| amount | DOUBLE PRECISION | NOT NULL | ✓ YES |
| sales_tax | DOUBLE PRECISION | NULL | ✓ YES |
| paid_total | DOUBLE PRECISION | NULL | ✓ YES |
| total | DOUBLE PRECISION | NULL | ✓ YES |
| cancelled_amount | NUMERIC(10, 2) | NOT NULL | ✓ YES |
| admin_commission_amount | NUMERIC(10, 2) | NOT NULL | ✓ YES |
| discount | DOUBLE PRECISION | NULL | ✓ YES |
| delivery_fee | DOUBLE PRECISION | NULL | ✓ YES |
| coupon_discount | DOUBLE PRECISION | NULL | ✓ YES |

---

### 2. ORDER_PRODUCT (6 fields)
| Field Name | Type | Nullable | Format to 2 decimals? |
|------------|------|----------|----------------------|
| unit_price | DOUBLE PRECISION | NOT NULL | ✓ YES |
| subtotal | DOUBLE PRECISION | NOT NULL | ✓ YES |
| admin_commission | NUMERIC(10, 2) | NOT NULL | ✓ YES |
| sale_price | DOUBLE PRECISION | NULL | ✓ YES |
| item_discount | DOUBLE PRECISION | NULL | ✓ YES |
| item_tax | DOUBLE PRECISION | NULL | ✓ YES |

---

### 3. PRODUCTS (9 fields)
| Field Name | Type | Nullable | Format to 2 decimals? |
|------------|------|----------|----------------------|
| **price** | DOUBLE PRECISION | NULL | ✓ YES |
| **sale_price** | DOUBLE PRECISION | NULL | ✓ YES |
| **purchase_price** | DOUBLE PRECISION | NULL | ✓ YES |
| **min_price** | DOUBLE PRECISION | NULL | ✓ YES |
| **max_price** | DOUBLE PRECISION | NULL | ✓ YES |
| height | DOUBLE PRECISION | NULL | ? **ASK USER** |
| width | DOUBLE PRECISION | NULL | ? **ASK USER** |
| length | DOUBLE PRECISION | NULL | ? **ASK USER** |
| weight | DOUBLE PRECISION | NULL | ? **ASK USER** |

**Note:** height, width, length, weight are dimensions/measurements, not monetary values

---

### 4. VARIATION_OPTIONS (1 field)
| Field Name | Type | Nullable | Format to 2 decimals? |
|------------|------|----------|----------------------|
| purchase_price | DOUBLE PRECISION | NULL | ✓ YES |

---

### 5. SHOP_EARNINGS (3 fields)
| Field Name | Type | Nullable | Format to 2 decimals? |
|------------|------|----------|----------------------|
| order_amount | NUMERIC(12, 2) | NOT NULL | ✓ YES |
| admin_commission | NUMERIC(12, 2) | NOT NULL | ✓ YES |
| shop_earning | NUMERIC(12, 2) | NOT NULL | ✓ YES |

---

### 6. WALLET_TRANSACTIONS (2 fields)
| Field Name | Type | Nullable | Format to 2 decimals? |
|------------|------|----------|----------------------|
| amount | DOUBLE PRECISION | NOT NULL | ✓ YES |
| balance_after | DOUBLE PRECISION | NOT NULL | ✓ YES |

---

### 7. SHOP_WITHDRAW_REQUESTS (1 field)
| Field Name | Type | Nullable | Format to 2 decimals? |
|------------|------|----------|----------------------|
| amount | DOUBLE PRECISION | NOT NULL | ✓ YES |

---

### 8. RETURN_REQUEST (3 fields)
| Field Name | Type | Nullable | Format to 2 decimals? |
|------------|------|----------|----------------------|
| refund_amount | DOUBLE PRECISION | NULL | ✓ YES |
| restocking_fee | DOUBLE PRECISION | NULL | ✓ YES |
| approved_amount | DOUBLE PRECISION | NULL | ✓ YES |

---

### 9. PRODUCT_PURCHASE (6 fields)
| Field Name | Type | Nullable | Format to 2 decimals? |
|------------|------|----------|----------------------|
| unit_purchase_price | DOUBLE PRECISION | NOT NULL | ✓ YES |
| total_cost | DOUBLE PRECISION | NOT NULL | ✓ YES |
| shipping_cost | DOUBLE PRECISION | NULL | ✓ YES |
| tax_amount | DOUBLE PRECISION | NULL | ✓ YES |
| discount_amount | DOUBLE PRECISION | NULL | ✓ YES |
| net_amount | DOUBLE PRECISION | NOT NULL | ✓ YES |

---

## Tables with NO numeric fields:
- users ✓ (no float/double fields)
- wallets ✗ (table not found/error)
- return_items ✗ (table not found/error)

---

## Summary by Category

### Monetary Fields (CONFIRMED - need 2 decimals):
**Total: 38 fields**

**Price fields (9):**
- price, sale_price, purchase_price, min_price, max_price (products)
- purchase_price (variation_options)
- unit_price, sale_price (order_product)
- unit_purchase_price (product_purchase)

**Amount fields (10):**
- amount, paid_total, cancelled_amount (orders)
- amount, balance_after (wallet_transactions)
- amount (shop_withdraw_requests)
- order_amount (shop_earnings)
- refund_amount, approved_amount (return_request)
- total_cost, net_amount (product_purchase)

**Discount fields (4):**
- discount, coupon_discount (orders)
- item_discount (order_product)
- discount_amount (product_purchase)

**Tax/Fee fields (7):**
- sales_tax, delivery_fee (orders)
- item_tax (order_product)
- restocking_fee (return_request)
- shipping_cost, tax_amount (product_purchase)

**Subtotal fields (1):**
- subtotal (order_product)

**Commission/Earnings fields (4):**
- admin_commission_amount (orders)
- admin_commission (order_product)
- admin_commission, shop_earning (shop_earnings)

**Other monetary fields (3):**
- total (orders)

### Dimension/Measurement Fields (NEED CONFIRMATION):
**Total: 4 fields**

- height (products) - physical dimension
- width (products) - physical dimension
- length (products) - physical dimension
- weight (products) - physical weight

**Question:** Should dimension/measurement fields also be formatted to 2 decimals?
- If YES: formats like 10.50 cm, 5.75 kg
- If NO: can keep more precision like 10.567 cm, 5.789 kg

---

## Recommendation

### Implement 2 decimal formatting for:
✅ **All 38 monetary fields** (already confirmed by user)

### Ask user about:
❓ **4 dimension/measurement fields** in products table:
  - height
  - width
  - length
  - weight

Should these also be formatted to 2 decimals, or keep higher precision?
