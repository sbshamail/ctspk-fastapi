# Notification Analysis for Order 93

## Order Details

**Order ID:** 93
**Tracking Number:** TRK-5FC0A781350B
**Customer ID:** 11 (M.Ghalib Raza - rurazza@gmail.com)
**Total Amount:** $9,295.00
**Created At:** 2025-12-04 14:21:41

---

## Order Products & Shops

The order contains products from **2 different shops**:

| Product ID | Shop ID | Shop Name | Quantity |
|------------|---------|-----------|----------|
| 276 | 3 | D.Watson Cash & Carry | 1.0 |
| 281 | 1 | Hatim Super Market | 1.0 |

---

## Shop Ownership & User Relationships

### Shop 1: Hatim Super Market
- **Owner:** User 9 (hamail@example.com) - NOT in `user_shop` table
- **Staff/Users in `user_shop` table:**
  - User 10 (user staff - test@example.com)

### Shop 3: D.Watson Cash & Carry
- **Owner:** User 9 (hamail@example.com) - NOT in `user_shop` table
- **Staff/Users in `user_shop` table:**
  - **NONE** ❌

---

## Current Notifications Sent (ONLY 3)

| Notification ID | User ID | User Name | User Type | Message |
|-----------------|---------|-----------|-----------|---------|
| 10 | 11 | M.Ghalib Raza | Customer | Your order **TRK-5FC0A781350B** has been placed successfully. Total: **$9295.0** |
| 11 | 10 | user staff | Shop Staff | New order **TRK-5FC0A781350B** received for shop **Hatim Super Market**. |
| 12 | 8 | admin | Admin (is_root=True) | New order **TRK-5FC0A781350B** has been placed. Total: **$9295.0** |

---

## ❌ PROBLEM IDENTIFIED

### Missing Notifications:

1. **User 9 (hamail) - Shop Owner**
   - Owns BOTH shops (Shop 1 AND Shop 3)
   - Should receive **2 notifications** (one for each shop)
   - Received: **0 notifications** ❌

   **Missing notifications:**
   - ❌ "New order TRK-5FC0A781350B received for shop **Hatim Super Market**"
   - ❌ "New order TRK-5FC0A781350B received for shop **D.Watson Cash & Carry**"

2. **Shop 3 (D.Watson Cash & Carry) - No users at all**
   - Has **NO entries** in `user_shop` table
   - Owner (User 9) not in `user_shop` table
   - Result: **No one** was notified about products from Shop 3 ❌

---

## Root Cause Analysis

### Issue 1: Shop Owners Not in `user_shop` Table

The current notification logic **ONLY queries the `user_shop` table**:

```python
# From notification_helper.py line 224-227
user_shops = session.exec(
    select(UserShop).where(UserShop.shop_id == shop_id)
).all()

for user_shop in user_shops:
    # Send notification
```

**Problem:** Shop owners are defined in `shops.owner_id`, NOT in `user_shop` table.

**Current Database State:**
```sql
-- Query: Get shop owners
SELECT id, name, owner_id FROM shops WHERE id IN (1, 3);

Result:
  Shop 1 - Owner: User 9 (hamail)
  Shop 3 - Owner: User 9 (hamail)

-- Query: Get users in user_shop for these shops
SELECT user_id, shop_id FROM user_shop WHERE shop_id IN (1, 3);

Result:
  Shop 1: User 10 only
  Shop 3: NO USERS ❌
```

**Expected Behavior:**
- User 9 should receive notification for Shop 1
- User 9 should receive notification for Shop 3
- User 10 should receive notification for Shop 1

**Actual Behavior:**
- User 9 received 0 notifications ❌
- User 10 received 1 notification for Shop 1 ✓
- Shop 3 had NO notifications sent ❌

---

## SQL Queries Used by Current Code

### Query 1: Get Order Details
```sql
SELECT * FROM orders WHERE id = 93;
```

### Query 2: Get Order Products & Shop IDs
```sql
SELECT product_id, shop_id, order_quantity
FROM order_product
WHERE order_id = 93;
```
**Result:** shop_ids = [1, 3]

### Query 3: Get Shop Users (Current Implementation - INCOMPLETE)
```sql
-- For Shop 1
SELECT user_id FROM user_shop WHERE shop_id = 1;
-- Returns: [10]

-- For Shop 3
SELECT user_id FROM user_shop WHERE shop_id = 3;
-- Returns: [] ❌ EMPTY!
```

### Query 4: Get Admin Users
```sql
SELECT id FROM users WHERE is_root = TRUE;
-- Returns: [8]
```

### Query 5: Create Notifications
```sql
-- Customer notification
INSERT INTO notifications (user_id, message, sent_at, is_read)
VALUES (11, 'Your order TRK-5FC0A781350B has been placed...', NOW(), false);

-- Shop 1 staff notification
INSERT INTO notifications (user_id, message, sent_at, is_read)
VALUES (10, 'New order TRK-5FC0A781350B received for shop Hatim Super Market.', NOW(), false);

-- Admin notification
INSERT INTO notifications (user_id, message, sent_at, is_read)
VALUES (8, 'New order TRK-5FC0A781350B has been placed...', NOW(), false);
```

---

## Required SQL Queries for Correct Behavior

### Corrected Query: Get ALL Shop Users (Owners + Staff)

```sql
-- For each shop_id, get BOTH owner AND staff
-- Option 1: UNION query
SELECT DISTINCT user_id, shop_id, 'owner' as role
FROM shops
WHERE id = :shop_id
  AND owner_id IS NOT NULL
UNION
SELECT user_id, shop_id, 'staff' as role
FROM user_shop
WHERE shop_id = :shop_id;

-- For Shop 1:
-- Returns: [(9, 1, 'owner'), (10, 1, 'staff')]

-- For Shop 3:
-- Returns: [(9, 3, 'owner')] ✓ (was missing before!)
```

### Expected Notifications After Fix

```sql
-- 1. Customer notification (User 11)
INSERT INTO notifications (user_id, message, sent_at, is_read)
VALUES (11, 'Your order TRK-5FC0A781350B has been placed successfully. Total: $9295.0', NOW(), false);

-- 2. Shop 1 - Owner notification (User 9)
INSERT INTO notifications (user_id, message, sent_at, is_read)
VALUES (9, 'New order TRK-5FC0A781350B received for shop Hatim Super Market.', NOW(), false);

-- 3. Shop 1 - Staff notification (User 10)
INSERT INTO notifications (user_id, message, sent_at, is_read)
VALUES (10, 'New order TRK-5FC0A781350B received for shop Hatim Super Market.', NOW(), false);

-- 4. Shop 3 - Owner notification (User 9) ✓ NEW!
INSERT INTO notifications (user_id, message, sent_at, is_read)
VALUES (9, 'New order TRK-5FC0A781350B received for shop D.Watson Cash & Carry.', NOW(), false);

-- 5. Admin notification (User 8)
-- Note: User 9 already got shop notifications, so skip admin notification for them
INSERT INTO notifications (user_id, message, sent_at, is_read)
VALUES (8, 'New order TRK-5FC0A781350B has been placed. Total: $9295.0', NOW(), false);
```

**Total Expected Notifications:** 5
**Currently Sent:** 3 ❌

---

## Summary

### Current State (BROKEN):
- ✓ Customer notified: 1 notification
- ✗ Shop 1 notifications: Only staff (User 10), **owner missing** (User 9)
- ✗ Shop 3 notifications: **NONE** (no users in user_shop table)
- ✓ Admin notified: 1 notification
- **Total:** 3 notifications

### Expected State (AFTER FIX):
- ✓ Customer notified: 1 notification
- ✓ Shop 1 notifications: Owner (User 9) + Staff (User 10) = 2 notifications
- ✓ Shop 3 notifications: Owner (User 9) = 1 notification
  *(User 9 gets BOTH shop notifications with different shop names)*
- ✓ Admin notified: 1 notification (User 8 only, User 9 skipped as already notified)
- **Total:** 5 notifications

---

## Recommendation

**CRITICAL FIX NEEDED:** Update `NotificationHelper.notify_order_placed()` to include shop owners from `shops.owner_id`, not just users from `user_shop` table.

The fix should:
1. Query shop owner from `shops.owner_id`
2. Query staff from `user_shop` table
3. Merge both lists (removing duplicates)
4. Send notifications to all users with shop-specific messages
