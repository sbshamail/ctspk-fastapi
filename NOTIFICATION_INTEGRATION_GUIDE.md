# 🔔 Notification System Integration Guide

Complete guide for integrating notifications throughout the application.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Integration by Feature](#integration-by-feature)
4. [Scheduled Tasks Setup](#scheduled-tasks-setup)
5. [Testing](#testing)

---

## Overview

The notification system consists of:
- **`notification_helper.py`** - Core notification functions
- **`notification_tasks.py`** - Background/scheduled tasks
- **Notification Model** - Already created in `notificationModel.py`

---

## Quick Start

### Import the Helper

```python
from src.api.core.notification_helper import notification_helper
# OR use shortcut functions
from src.api.core.notification_helper import (
    notify_user_registered,
    notify_shop_created,
    notify_order_placed
)
```

---

## Integration by Feature

### 1. User Registration

**File:** `src/api/routers/authRoute.py`

**Location:** After user is created and committed

```python
# In register_user function, after session.commit()
from src.api.core.notification_helper import notification_helper

# After: session.commit()
notification_helper.notify_user_registered(session, user.id, user.name)
```

---

### 2. Shop Management

#### A. Shop Creation

**File:** `src/api/routers/shopRoute.py`

**Location:** In `create_shop` function, after shop is created

```python
from src.api.core.notification_helper import notification_helper

# After: session.commit()
notification_helper.notify_shop_created(session, shop.id, shop.name)
```

#### B. Shop Approval

**File:** `src/api/routers/shopRoute.py`

**Location:** In shop approval endpoint

```python
# When approving shop
if new_status == "approved":
    notification_helper.notify_shop_approved(session, shop_id)
elif new_status == "disapproved":
    notification_helper.notify_shop_disapproved(
        session,
        shop_id,
        reason="Reason for disapproval"  # Optional
    )
```

---

### 3. Product Stock Notifications

#### A. Low Stock Alert

**File:** `src/api/routers/productRoute.py`

**Location:** After product quantity is updated (in update product or after order)

```python
from src.api.core.notification_helper import notification_helper

# After updating product quantity
if product.quantity > 0 and product.quantity <= 10:
    notification_helper.notify_product_low_stock(
        session,
        product.shop_id,
        product.name,
        product.quantity,
        threshold=10
    )
```

#### B. Out of Stock Alert

```python
# When product quantity reaches 0
if product.quantity == 0:
    notification_helper.notify_product_out_of_stock(
        session,
        product.shop_id,
        product.name
    )
```

#### C. Back in Stock (for Wishlist Users)

**File:** `src/api/routers/productRoute.py`

**Location:** When product is restocked

```python
from src.api.models.wishlistModel import Wishlist

# When product quantity is increased from 0
if old_quantity == 0 and new_quantity > 0:
    # Get all users who wishlisted this product
    wishlist_users = session.exec(
        select(Wishlist).where(Wishlist.product_id == product.id)
    ).scalars().all()

    for wishlist_item in wishlist_users:
        notification_helper.notify_product_back_in_stock(
            session,
            wishlist_item.user_id,
            product.name
        )
```

---

### 4. Order Notifications

#### A. Order Placed

**File:** `src/api/routers/orderRoute.py`

**Location:** In order creation endpoint, after order is committed

```python
from src.api.core.notification_helper import notification_helper

# After: session.commit()
# Get unique shop IDs from order products
shop_ids = list(set([op.shop_id for op in order.order_products if op.shop_id]))

notification_helper.notify_order_placed(
    session,
    order.id,
    order.tracking_number,
    order.customer_id,
    shop_ids,
    float(order.final_amount)
)
```

#### B. Order Status Changed

**File:** `src/api/routers/orderRoute.py`

**Location:** In update_status endpoint, after status is changed

```python
# After: order.order_status = new_status
# After: session.commit()

notification_helper.notify_order_status_changed(
    session,
    order.id,
    order.tracking_number,
    order.customer_id,
    new_status.value  # or str(new_status)
)
```

#### C. Order Cancelled

**File:** `src/api/routers/orderRoute.py`

**Location:** In cancel_order and admin_cancel endpoints

```python
# Get shop IDs
shop_ids = list(set([op.shop_id for op in order.order_products if op.shop_id]))

# After cancellation
notification_helper.notify_order_cancelled(
    session,
    order.id,
    order.tracking_number,
    order.customer_id,
    shop_ids,
    cancelled_by="customer"  # or "admin"
)
```

#### D. Order Returned/Refunded

**File:** `src/api/routers/orderRoute.py` or `returnRoute.py`

**Location:** When order is marked as refunded

```python
shop_ids = list(set([op.shop_id for op in order.order_products if op.shop_id]))

notification_helper.notify_order_returned(
    session,
    order.id,
    order.tracking_number,
    order.customer_id,
    shop_ids
)
```

#### E. Order Assigned to Fulfillment

**File:** `src/api/routers/orderRoute.py`

**Location:** When fulfillment_id is assigned to order

```python
# When setting order.fullfillment_id
if order.fullfillment_id and order.fullfillment_id > 0:
    notification_helper.notify_order_assigned_to_fulfillment(
        session,
        order.id,
        order.tracking_number,
        order.customer_id,
        order.fullfillment_id
    )
```

---

### 5. Withdrawal Notifications

#### A. Withdrawal Request Created

**File:** `src/api/routers/withdrawRoute.py`

**Location:** In `create_withdraw_request`, after commit

```python
from src.api.core.notification_helper import notification_helper

# After: session.commit()
notification_helper.notify_withdrawal_requested(
    session,
    withdraw_request.shop_id,
    float(withdraw_request.amount),
    withdraw_request.id
)
```

#### B. Withdrawal Approved

**File:** `src/api/routers/withdrawRoute.py`

**Location:** In `approve_withdraw_request`, after commit

```python
# After: session.commit()
notification_helper.notify_withdrawal_approved(
    session,
    withdraw_request.shop_id,
    float(withdraw_request.amount)
)
```

#### C. Withdrawal Rejected

**File:** `src/api/routers/withdrawRoute.py`

**Location:** In `reject_withdraw_request`, after commit

```python
# After: session.commit()
notification_helper.notify_withdrawal_rejected(
    session,
    withdraw_request.shop_id,
    float(withdraw_request.amount),
    rejection_reason  # From request parameter
)
```

#### D. Withdrawal Processed

**File:** `src/api/routers/withdrawRoute.py`

**Location:** In `process_withdraw_request`, after commit

```python
# After: session.commit()
notification_helper.notify_withdrawal_processed(
    session,
    withdraw_request.shop_id,
    float(withdraw_request.amount),
    float(withdraw_request.net_amount)
)
```

---

## Scheduled Tasks Setup

### Background Tasks (Cron Jobs)

The following tasks should run automatically:

1. **Wishlist Reminders** - Daily at 9 AM
2. **Cart Reminders** - Daily at 9 AM
3. **Low Stock Check** - Daily at 8 AM
4. **Out of Stock Check** - Daily at 8 AM

### Setup on Linux/Mac

Edit crontab:
```bash
crontab -e
```

Add these lines:
```bash
# Wishlist & Cart Reminders (9 AM daily)
0 9 * * * cd /path/to/ctspk-fastapi && /path/to/.venv/bin/python -m src.api.core.notification_tasks

# Low Stock Check (8 AM daily)
0 8 * * * cd /path/to/ctspk-fastapi && /path/to/.venv/bin/python -c "from src.api.core.notification_tasks import check_low_stock_products, check_out_of_stock_products; check_low_stock_products(); check_out_of_stock_products()"
```

### Setup on Windows (Task Scheduler)

1. Open Task Scheduler
2. Create New Task
3. Set Trigger: Daily at 9:00 AM
4. Set Action:
   - Program: `C:\ctspk-fastapi\.venv\Scripts\python.exe`
   - Arguments: `C:\ctspk-fastapi\src\api\core\notification_tasks.py`
   - Start in: `C:\ctspk-fastapi`

### Manual Testing

Run tasks manually:
```bash
python src/api/core/notification_tasks.py
```

---

## Testing

### Test Individual Notifications

```python
from sqlmodel import Session
from src.lib.db_con import engine
from src.api.core.notification_helper import notification_helper

with Session(engine) as session:
    # Test user registration notification
    notification_helper.notify_user_registered(session, user_id=1, user_name="John Doe")

    # Test shop creation notification
    notification_helper.notify_shop_created(session, shop_id=1, shop_name="My Shop")

    # Test order placed notification
    notification_helper.notify_order_placed(
        session,
        order_id=1,
        tracking_number="TRK-123",
        customer_id=1,
        shop_ids=[1, 2],
        total_amount=99.99
    )
```

### Check Notifications in Database

```sql
-- View all notifications
SELECT * FROM notifications ORDER BY created_at DESC LIMIT 10;

-- View unread notifications for user
SELECT * FROM notifications
WHERE user_id = 1 AND is_read = false
ORDER BY created_at DESC;

-- Count notifications by user
SELECT user_id, COUNT(*) as total
FROM notifications
GROUP BY user_id;
```

---

## Summary Checklist

- [ ] ✅ User Registration - `authRoute.py`
- [ ] ✅ Shop Created - `shopRoute.py`
- [ ] ✅ Shop Approved/Disapproved - `shopRoute.py`
- [ ] ✅ Product Low Stock - `productRoute.py`
- [ ] ✅ Product Out of Stock - `productRoute.py`
- [ ] ✅ Product Back in Stock - `productRoute.py`
- [ ] ✅ Order Placed - `orderRoute.py`
- [ ] ✅ Order Status Changed - `orderRoute.py`
- [ ] ✅ Order Cancelled - `orderRoute.py`
- [ ] ✅ Order Returned - `orderRoute.py` or `returnRoute.py`
- [ ] ✅ Order Assigned to Fulfillment - `orderRoute.py`
- [ ] ✅ Withdrawal Requested - `withdrawRoute.py`
- [ ] ✅ Withdrawal Approved - `withdrawRoute.py`
- [ ] ✅ Withdrawal Rejected - `withdrawRoute.py`
- [ ] ✅ Withdrawal Processed - `withdrawRoute.py`
- [ ] ⏰ Wishlist Reminders - Background Task
- [ ] ⏰ Cart Reminders - Background Task
- [ ] ⏰ Low Stock Check - Background Task

---

## Quick Reference - All Notification Types

| Event | Who Gets Notified | Function |
|-------|-------------------|----------|
| User Registration | User | `notify_user_registered()` |
| Shop Created | Owner + All Root Users | `notify_shop_created()` |
| Shop Approved | Owner | `notify_shop_approved()` |
| Shop Disapproved | Owner | `notify_shop_disapproved()` |
| Low Stock | Shop Owner | `notify_product_low_stock()` |
| Out of Stock | Shop Owner | `notify_product_out_of_stock()` |
| Back in Stock | Wishlist Users | `notify_product_back_in_stock()` |
| Wishlist Reminder (7 days) | User | `notify_wishlist_reminder()` |
| Cart Reminder (2 days) | User | `notify_cart_reminder()` |
| Order Placed | Customer + Shop Owners + Admins | `notify_order_placed()` |
| Order Status Changed | Customer | `notify_order_status_changed()` |
| Order Cancelled | Customer + Shop Owners + Admins | `notify_order_cancelled()` |
| Order Returned | Customer + Shop Owners + Admins | `notify_order_returned()` |
| Order Assigned | Fulfillment User + Customer | `notify_order_assigned_to_fulfillment()` |
| Withdrawal Requested | Shop Owner + Admins | `notify_withdrawal_requested()` |
| Withdrawal Approved | Shop Owner | `notify_withdrawal_approved()` |
| Withdrawal Rejected | Shop Owner | `notify_withdrawal_rejected()` |
| Withdrawal Processed | Shop Owner | `notify_withdrawal_processed()` |

---

**Need Help?** Check `src/api/core/notification_helper.py` for all available functions and their parameters.
