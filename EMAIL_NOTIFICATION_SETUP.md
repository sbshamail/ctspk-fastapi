# 📧 Email Notification System Setup Guide

Complete guide for the dual notification system (In-app + Email) for automated background tasks.

## 📋 Overview

The system now sends **BOTH** in-app notifications AND emails for:
- ✅ Wishlist reminders (after 7 days)
- ✅ Cart reminders (after 2 days)
- ✅ Low stock alerts (≤10 units)
- ✅ Out of stock alerts (0 units)
- ✅ Back in stock notifications

---

## 🗂️ File Structure

### Core Files Created

1. **`src/api/core/notification_helper.py`**
   - In-app notification functions
   - 20+ notification types
   - HTML message support

2. **`src/api/core/notification_tasks.py`**
   - Background tasks for scheduled operations
   - Sends BOTH notifications AND emails
   - Run via cron jobs

3. **`src/api/core/email_notification_helper.py`**
   - Email sending functions
   - Template-based system
   - User/shop owner email retrieval

4. **`NOTIFICATION_INTEGRATION_GUIDE.md`**
   - Integration instructions for routes
   - All notification types documented

---

## 🎯 Email Templates Required

You need to create these email templates in your database with the following IDs:

| Template ID | Purpose | Variables Needed |
|-------------|---------|------------------|
| **10** | Wishlist Reminder | `user_name`, `product_name`, `product_id`, `days`, `product_url`, `view_product_link`, `wishlist_url` |
| **11** | Cart Reminder | `user_name`, `item_count`, `total_amount`, `cart_url`, `checkout_url` |
| **12** | Low Stock Alert | `shop_name`, `owner_name`, `product_name`, `product_id`, `current_stock`, `threshold`, `product_url`, `inventory_url` |
| **13** | Out of Stock Alert | `shop_name`, `owner_name`, `product_name`, `product_id`, `product_url`, `restock_url` |
| **14** | Back in Stock | `user_name`, `product_name`, `product_id`, `product_url`, `shop_now_link` |

### Example Template Creation SQL

```sql
-- Template 10: Wishlist Reminder
INSERT INTO email_templates (id, name, subject, body, created_at, updated_at)
VALUES (
    10,
    'Wishlist Reminder',
    'Still interested in {{product_name}}?',
    '<h2>Hi {{user_name}},</h2>
    <p>You added <strong>{{product_name}}</strong> to your wishlist {{days}} days ago.</p>
    <p>The product is still available! Don''t miss out.</p>
    <p><a href="{{view_product_link}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Product</a></p>
    <p><a href="{{wishlist_url}}">View Your Wishlist</a></p>',
    NOW(),
    NOW()
);

-- Template 11: Cart Reminder
INSERT INTO email_templates (id, name, subject, body, created_at, updated_at)
VALUES (
    11,
    'Cart Reminder',
    'You have {{item_count}} item(s) waiting in your cart',
    '<h2>Hi {{user_name}},</h2>
    <p>You have <strong>{{item_count}}</strong> item(s) in your cart.</p>
    <p>Total: <strong>{{total_amount}}</strong></p>
    <p>Complete your purchase before they''re gone!</p>
    <p><a href="{{checkout_url}}" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Checkout Now</a></p>
    <p><a href="{{cart_url}}">View Your Cart</a></p>',
    NOW(),
    NOW()
);

-- Template 12: Low Stock Alert
INSERT INTO email_templates (id, name, subject, body, created_at, updated_at)
VALUES (
    12,
    'Low Stock Alert',
    'Low Stock Alert: {{product_name}}',
    '<h2>Hi {{owner_name}},</h2>
    <p><strong>Low Stock Alert for {{shop_name}}</strong></p>
    <p>Product: <strong>{{product_name}}</strong></p>
    <p>Current Stock: <strong>{{current_stock}}</strong> units (Threshold: {{threshold}})</p>
    <p>Please restock this product soon to avoid running out.</p>
    <p><a href="{{product_url}}" style="background-color: #FF9800; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Manage Product</a></p>
    <p><a href="{{inventory_url}}">View Inventory</a></p>',
    NOW(),
    NOW()
);

-- Template 13: Out of Stock Alert
INSERT INTO email_templates (id, name, subject, body, created_at, updated_at)
VALUES (
    13,
    'Out of Stock Alert',
    'URGENT: {{product_name}} is Out of Stock',
    '<h2>Hi {{owner_name}},</h2>
    <p><strong>Out of Stock Alert for {{shop_name}}</strong></p>
    <p>Product: <strong>{{product_name}}</strong></p>
    <p>This product is now completely out of stock!</p>
    <p>Please restock immediately to resume sales.</p>
    <p><a href="{{restock_url}}" style="background-color: #F44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Restock Now</a></p>
    <p><a href="{{product_url}}">Manage Product</a></p>',
    NOW(),
    NOW()
);

-- Template 14: Back in Stock
INSERT INTO email_templates (id, name, subject, body, created_at, updated_at)
VALUES (
    14,
    'Back in Stock',
    'Good News! {{product_name}} is back in stock',
    '<h2>Hi {{user_name}},</h2>
    <p><strong>Great news!</strong> A product from your wishlist is back in stock.</p>
    <p>Product: <strong>{{product_name}}</strong></p>
    <p>Don''t wait - it might sell out again!</p>
    <p><a href="{{shop_now_link}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Shop Now</a></p>',
    NOW(),
    NOW()
);
```

---

## ⚙️ Background Task Functions

All functions now send **both notifications AND emails**:

### 1. `send_wishlist_reminders()`
- **When:** Products in wishlist for 7+ days
- **Sends to:** Users who added products to wishlist
- **Notification:** In-app notification
- **Email:** Template ID 10
- **Schedule:** Daily at 9 AM

### 2. `send_cart_reminders()`
- **When:** Cart items older than 2 days
- **Sends to:** Users with abandoned carts
- **Notification:** In-app notification
- **Email:** Template ID 11 (includes cart total)
- **Schedule:** Daily at 9 AM

### 3. `check_low_stock_products()`
- **When:** Product stock ≤ 10 units
- **Sends to:** Shop owners
- **Notification:** In-app notification
- **Email:** Template ID 12
- **Schedule:** Daily at 8 AM

### 4. `check_out_of_stock_products()`
- **When:** Product stock = 0
- **Sends to:** Shop owners
- **Notification:** In-app notification
- **Email:** Template ID 13
- **Schedule:** Daily at 8 AM or when stock reaches 0

---

## 🚀 Setup Instructions

### Step 1: Create Email Templates

Run the SQL queries above to create email templates with IDs 10-14.

### Step 2: Test Manually

```bash
# Navigate to project directory
cd C:\ctspk-fastapi

# Activate virtual environment (if using one)
.venv\Scripts\activate  # Windows
# OR
source .venv/bin/activate  # Linux/Mac

# Run all tasks manually
python src/api/core/notification_tasks.py

# Or run individual tasks
python -c "from src.api.core.notification_tasks import send_wishlist_reminders; send_wishlist_reminders()"
python -c "from src.api.core.notification_tasks import send_cart_reminders; send_cart_reminders()"
python -c "from src.api.core.notification_tasks import check_low_stock_products; check_low_stock_products()"
python -c "from src.api.core.notification_tasks import check_out_of_stock_products; check_out_of_stock_products()"
```

### Step 3: Setup Automated Scheduling

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. **Name:** "Wishlist & Cart Reminders"
4. **Trigger:** Daily at 9:00 AM
5. **Action:** Start a program
   - **Program:** `C:\ctspk-fastapi\.venv\Scripts\python.exe`
   - **Arguments:** `C:\ctspk-fastapi\src\api\core\notification_tasks.py`
   - **Start in:** `C:\ctspk-fastapi`

6. Create another task for stock alerts:
   - **Name:** "Stock Alerts"
   - **Trigger:** Daily at 8:00 AM
   - **Program:** `C:\ctspk-fastapi\.venv\Scripts\python.exe`
   - **Arguments:** `-c "from src.api.core.notification_tasks import check_low_stock_products, check_out_of_stock_products; check_low_stock_products(); check_out_of_stock_products()"`
   - **Start in:** `C:\ctspk-fastapi`

#### Linux/Mac (Cron Jobs)

```bash
# Edit crontab
crontab -e

# Add these lines (adjust paths to match your setup)

# Wishlist & Cart Reminders - 9 AM daily
0 9 * * * cd /path/to/ctspk-fastapi && /path/to/.venv/bin/python -m src.api.core.notification_tasks >> /var/log/notifications.log 2>&1

# Stock Alerts - 8 AM daily
0 8 * * * cd /path/to/ctspk-fastapi && /path/to/.venv/bin/python -c "from src.api.core.notification_tasks import check_low_stock_products, check_out_of_stock_products; check_low_stock_products(); check_out_of_stock_products()" >> /var/log/stock_alerts.log 2>&1
```

---

## 📊 Monitoring

### Check Logs

The scripts print detailed logs:

```
🔔 Running wishlist reminder task...
✅ Wishlist reminder email sent to user@example.com
✅ Sent 5 wishlist notifications and 5 emails

🔔 Running cart reminder task...
✅ Cart reminder email sent to customer@example.com
✅ Sent 3 cart notifications and 3 emails

🔔 Running low stock check...
✅ Low stock email sent to shopowner@example.com
✅ Sent 2 low stock notifications and 2 emails

🔔 Running out of stock check...
✅ Out of stock email sent to shopowner@example.com
✅ Sent 1 out of stock notifications and 1 emails
```

### Check Database

```sql
-- Check recent notifications
SELECT * FROM notifications
WHERE created_at >= NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;

-- Check sent emails
SELECT * FROM email_logs
WHERE sent_at >= NOW() - INTERVAL '1 day'
ORDER BY sent_at DESC;
```

---

## 🔧 Configuration

### Adjust Thresholds

Edit `src/api/core/notification_tasks.py`:

```python
# Low stock threshold (default: 10)
LOW_STOCK_THRESHOLD = 10

# Wishlist reminder days (default: 7)
seven_days_ago = datetime.utcnow() - timedelta(days=7)

# Cart reminder days (default: 2)
two_days_ago = datetime.utcnow() - timedelta(days=2)
```

### Change Email Template IDs

Edit `src/api/core/email_notification_helper.py`:

```python
class EmailNotificationHelper:
    TEMPLATE_WISHLIST_REMINDER = 10
    TEMPLATE_CART_REMINDER = 11
    TEMPLATE_LOW_STOCK = 12
    TEMPLATE_OUT_OF_STOCK = 13
    TEMPLATE_BACK_IN_STOCK = 14
```

---

## 🎯 Summary

✅ **In-app notifications** - Created via `notification_helper.py`
✅ **Email notifications** - Created via `email_notification_helper.py`
✅ **Background tasks** - Send BOTH notifications AND emails
✅ **Scheduled execution** - Via cron jobs or Task Scheduler
✅ **5 Email templates** - IDs 10-14 need to be created in database

---

## 📝 Next Steps

1. ✅ Create email templates (IDs 10-14) in database
2. ✅ Test background tasks manually
3. ✅ Setup automated scheduling (cron/Task Scheduler)
4. ✅ Monitor logs to ensure emails are being sent
5. ✅ Follow `NOTIFICATION_INTEGRATION_GUIDE.md` to add notifications to routes

---

## 🆘 Troubleshooting

### Emails not sending?

1. Check email templates exist with correct IDs
2. Verify user emails are in database
3. Check email service configuration in `email_helper.py`
4. Check logs for error messages

### Notifications not appearing?

1. Verify notification_helper is imported correctly
2. Check database for notification records
3. Ensure session.commit() is called

### Tasks not running?

1. Check cron job or Task Scheduler is configured
2. Verify Python path and working directory
3. Check file permissions
4. Review system logs for errors

---

**For detailed integration into your routes, see `NOTIFICATION_INTEGRATION_GUIDE.md`**
