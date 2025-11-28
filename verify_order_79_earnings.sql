-- =====================================================
-- VERIFY SHOP EARNINGS FOR ORDER ID 79
-- =====================================================

-- 1. CHECK ORDER DETAILS
SELECT
    '=== ORDER DETAILS ===' as section,
    id as order_id,
    tracking_number,
    order_status,
    payment_status,
    total_amount,
    delivery_fee,
    discount_amount,
    final_amount,
    created_at,
    updated_at
FROM orders
WHERE id = 79;

-- 2. CHECK ORDER PRODUCTS (what was ordered)
SELECT
    '=== ORDER PRODUCTS ===' as section,
    op.id as order_product_id,
    op.order_id,
    op.product_id,
    p.name as product_name,
    op.shop_id,
    s.name as shop_name,
    op.quantity,
    op.price,
    op.subtotal,
    op.admin_commission,
    op.admin_commission_percent
FROM order_product op
LEFT JOIN products p ON op.product_id = p.id
LEFT JOIN shops s ON op.shop_id = s.id
WHERE op.order_id = 79
ORDER BY op.shop_id, op.id;

-- 3. CALCULATE EXPECTED EARNINGS (manual calculation)
SELECT
    '=== EXPECTED EARNINGS CALCULATION ===' as section,
    op.id as order_product_id,
    op.shop_id,
    s.name as shop_name,
    op.subtotal as product_subtotal,
    op.admin_commission,
    -- Calculate proportional delivery fee
    ROUND(
        CASE
            WHEN (SELECT SUM(subtotal) FROM order_product WHERE order_id = 79) > 0
            THEN (SELECT delivery_fee FROM orders WHERE id = 79) *
                 (op.subtotal / (SELECT SUM(subtotal) FROM order_product WHERE order_id = 79))
            ELSE 0
        END,
        2
    ) as proportional_delivery_fee,
    -- Calculate expected shop earning
    ROUND(
        op.subtotal -
        op.admin_commission -
        CASE
            WHEN (SELECT SUM(subtotal) FROM order_product WHERE order_id = 79) > 0
            THEN (SELECT delivery_fee FROM orders WHERE id = 79) *
                 (op.subtotal / (SELECT SUM(subtotal) FROM order_product WHERE order_id = 79))
            ELSE 0
        END,
        2
    ) as expected_shop_earning
FROM order_product op
LEFT JOIN shops s ON op.shop_id = s.id
WHERE op.order_id = 79
ORDER BY op.shop_id, op.id;

-- 4. CHECK ACTUAL SHOP EARNINGS IN DATABASE
SELECT
    '=== ACTUAL SHOP EARNINGS IN DB ===' as section,
    se.id as earning_id,
    se.shop_id,
    s.name as shop_name,
    se.order_id,
    se.order_product_id,
    se.order_amount,
    se.admin_commission,
    se.shop_earning,
    se.is_settled,
    se.settled_at,
    se.created_at
FROM shop_earnings se
LEFT JOIN shops s ON se.shop_id = s.id
WHERE se.order_id = 79
ORDER BY se.shop_id, se.id;

-- 5. COMPARE EXPECTED VS ACTUAL (shows if there are discrepancies)
SELECT
    '=== COMPARISON (Expected vs Actual) ===' as section,
    calc.order_product_id,
    calc.shop_id,
    calc.shop_name,
    calc.product_subtotal,
    calc.admin_commission as calc_admin_commission,
    calc.proportional_delivery_fee as calc_delivery_fee,
    calc.expected_shop_earning,
    COALESCE(se.shop_earning, 0) as actual_shop_earning,
    CASE
        WHEN se.id IS NULL THEN '❌ MISSING'
        WHEN ROUND(calc.expected_shop_earning - se.shop_earning, 2) = 0 THEN '✅ CORRECT'
        ELSE '⚠️ MISMATCH: Diff = ' || ROUND(calc.expected_shop_earning - se.shop_earning, 2)
    END as status
FROM (
    SELECT
        op.id as order_product_id,
        op.shop_id,
        s.name as shop_name,
        op.subtotal as product_subtotal,
        op.admin_commission,
        ROUND(
            CASE
                WHEN (SELECT SUM(subtotal) FROM order_product WHERE order_id = 79) > 0
                THEN (SELECT delivery_fee FROM orders WHERE id = 79) *
                     (op.subtotal / (SELECT SUM(subtotal) FROM order_product WHERE order_id = 79))
                ELSE 0
            END,
            2
        ) as proportional_delivery_fee,
        ROUND(
            op.subtotal -
            op.admin_commission -
            CASE
                WHEN (SELECT SUM(subtotal) FROM order_product WHERE order_id = 79) > 0
                THEN (SELECT delivery_fee FROM orders WHERE id = 79) *
                     (op.subtotal / (SELECT SUM(subtotal) FROM order_product WHERE order_id = 79))
                ELSE 0
            END,
            2
        ) as expected_shop_earning
    FROM order_product op
    LEFT JOIN shops s ON op.shop_id = s.id
    WHERE op.order_id = 79
) calc
LEFT JOIN shop_earnings se ON se.order_product_id = calc.order_product_id AND se.order_id = 79;

-- 6. SUMMARY BY SHOP
SELECT
    '=== SHOP SUMMARY ===' as section,
    s.id as shop_id,
    s.name as shop_name,
    COUNT(se.id) as number_of_earning_records,
    SUM(se.order_amount) as total_order_amount,
    SUM(se.admin_commission) as total_admin_commission,
    SUM(se.shop_earning) as total_shop_earning,
    STRING_AGG(CASE WHEN se.is_settled THEN 'Settled' ELSE 'Unsettled' END, ', ') as settlement_status
FROM shop_earnings se
LEFT JOIN shops s ON se.shop_id = s.id
WHERE se.order_id = 79
GROUP BY s.id, s.name
ORDER BY s.id;

-- 7. CHECK FOR DUPLICATE EARNINGS (should return 0 rows)
SELECT
    '=== DUPLICATE CHECK ===' as section,
    order_id,
    order_product_id,
    COUNT(*) as duplicate_count,
    CASE
        WHEN COUNT(*) > 1 THEN '❌ DUPLICATE FOUND!'
        ELSE '✅ No duplicates'
    END as status
FROM shop_earnings
WHERE order_id = 79
GROUP BY order_id, order_product_id
HAVING COUNT(*) > 1;
