# Order Email Cron Job - Complete Documentation

## Overview

This system automatically sends order notification emails to shop owners every 5 minutes. When an order contains products from multiple shops, each shop owner receives an email with **only their products** and relevant order information.

---

## 🎯 Features

✅ **Automatic Email Delivery** - Runs every 5 minutes
✅ **Multi-Shop Support** - Each shop owner gets their own customized email
✅ **Modern Responsive Template** - Beautiful HTML email with product images
✅ **Invoice Details** - Complete order breakdown with totals
✅ **Product Images** - Shows product thumbnails in email
✅ **Duplicate Prevention** - Tracks emails sent to avoid duplicates
✅ **Background Processing** - Doesn't block application performance

---

## 📂 Files Created

### 1. **Email Template**
```
src/api/templates/order_email_template.html
```
- Modern, responsive HTML email template
- Includes product images, prices, and customer information
- Mobile-friendly design
- Professional invoice layout

### 2. **Email Service**
```
src/api/services/order_email_service.py
```
- `OrderEmailService` class for email generation
- Filters products by shop
- Calculates shop-specific totals
- Generates HTML from template

### 3. **Cron Job Service**
```
src/api/services/order_email_cron.py
```
- `OrderEmailCron` class for scheduled execution
- Runs every 5 minutes
- Processes pending orders
- Tracks email status

### 4. **Cron Startup Module**
```
src/api/core/cron_startup.py
```
- Initializes cron jobs on app startup
- Stops cron jobs on app shutdown
- Can be enabled/disabled via environment variable

### 5. **Requirements**
```
requirements_cron.txt
```
- Additional Python dependencies

---

## 🚀 Installation

### Step 1: Install Dependencies

```bash
pip install schedule==1.2.0
```

Or install from requirements file:
```bash
pip install -r requirements_cron.txt
```

### Step 2: Configure Environment Variables

Add to your `.env` file:

```env
# Email Configuration (already exists)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=Your Store Name

# Site Configuration
BASE_URL=http://localhost:3000
SITE_NAME=Your Store

# Cron Job Configuration (optional)
ENABLE_CRON_JOBS=true
```

### Step 3: Application Already Configured

The cron job is automatically started when your FastAPI application starts (already updated in `src/main.py`).

---

## 📧 Email Template Variables

The email template uses the following variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{order_tracking_number}}` | Order tracking number | TRK-ABC123 |
| `{{order_date}}` | Order creation date | December 02, 2025 02:30 PM |
| `{{payment_status}}` | Payment status | Paid / Pending |
| `{{order_status}}` | Order status | order-pending |
| `{{shop_name}}` | Shop name | Tech Store |
| `{{products_html}}` | HTML for product list | (auto-generated) |
| `{{shop_subtotal}}` | Subtotal for shop | 150.00 |
| `{{shop_tax}}` | Tax amount for shop | 15.00 |
| `{{shop_discount}}` | Discount for shop | 10.00 |
| `{{shop_total}}` | Total for shop | 155.00 |
| `{{customer_name}}` | Customer name | John Doe |
| `{{customer_contact}}` | Customer phone | +1234567890 |
| `{{customer_email}}` | Customer email | john@example.com |
| `{{shipping_address}}` | Formatted address | 123 Main St, City, State |
| `{{dashboard_link}}` | Link to dashboard | http://localhost:3000/dashboard |
| `{{site_name}}` | Your site name | Your Store |
| `{{current_year}}` | Current year | 2025 |

---

## 🔧 How It Works

### 1. **Order Placement**
When a customer places an order with products from multiple shops:
```
Order #TRK-001
├── Shop A: Product 1, Product 2
└── Shop B: Product 3, Product 4
```

### 2. **Cron Job Execution (Every 5 Minutes)**
```
1. Query orders created in last 10 minutes
2. Filter out orders that already have emails sent
3. For each order:
   ├── Get unique shop IDs
   ├── For each shop:
   │   ├── Filter products for that shop
   │   ├── Calculate shop-specific totals
   │   ├── Generate customized email
   │   └── Send to shop owner's email
   └── Mark order as email sent
```

### 3. **Email Sent**
- **Shop A Owner** receives email with Products 1 & 2 only
- **Shop B Owner** receives email with Products 3 & 4 only
- Each email shows correct totals for that shop

---

## 📊 Email Tracking

The system tracks sent emails using order metadata:

```python
order.metadata = {
    'shop_owner_email_sent': True,
    'shop_owner_email_sent_at': '2025-12-02T14:30:00'
}
```

### Duplicate Prevention
- Orders created more than 10 minutes ago are skipped
- Orders with `shop_owner_email_sent: True` are skipped
- Prevents sending duplicate emails

---

## 🎨 Email Template Features

### Responsive Design
- ✅ Desktop optimized
- ✅ Mobile friendly
- ✅ Works in all email clients

### Email Sections

1. **Header**
   - Eye-catching gradient background
   - Order tracking number
   - Welcome message

2. **Order Information Box**
   - Order number
   - Order date
   - Payment status
   - Order status

3. **Products Section**
   - Product images (100x100px)
   - Product name and SKU
   - Quantity
   - Unit price (with sale price if applicable)
   - Item total
   - Variation details (if applicable)

4. **Totals Section**
   - Subtotal
   - Tax
   - Discount
   - **Grand Total** (highlighted)

5. **Customer Information**
   - Customer name, email, phone
   - Shipping address

6. **Alert Box**
   - Important reminder to process within 24 hours

7. **Action Button**
   - "View Order Details" link to dashboard

8. **Footer**
   - Site information
   - Support links
   - Copyright notice

---

## 🛠️ Manual Testing

### Run Cron Job Manually

You can test the cron job without waiting 5 minutes:

```bash
python -m src.api.services.order_email_cron
```

This will:
1. Process all pending orders
2. Send emails to shop owners
3. Display detailed logs

### Test Email Sending

```python
from sqlmodel import Session
from src.lib.db_con import engine
from src.api.services.order_email_service import order_email_service
from src.api.models.order_model.orderModel import Order

session = Session(engine)

# Get an order
order = session.get(Order, 1)  # Replace with actual order ID

# Send email to specific shop
success = order_email_service.send_order_email_to_shop_owner(
    session=session,
    order=order,
    shop_id=1  # Replace with actual shop ID
)

print(f"Email sent: {success}")
```

---

## 🔍 Monitoring & Logs

### Cron Job Logs

When the cron job runs, you'll see detailed logs:

```
============================================================
🔄 Order Email Cron Job Running at 2025-12-02 14:30:00
============================================================
📊 Found 3 orders to process

📦 Processing Order #TRK-ABC123
   Order ID: 1
   Created: 2025-12-02 14:25:00
   Status: order-pending
   🏪 Shops involved: 2
   📧 Emails sent: 2/2
      Shop 1: ✅ Sent
      Shop 2: ✅ Sent
   ✅ Order marked as email sent

============================================================
✅ Cron job completed successfully
============================================================
```

### Application Startup Logs

When your app starts:

```
🟢 Application starting up...

============================================================
🚀 Initializing Cron Jobs
============================================================
🚀 Starting Order Email Cron Job
   Schedule: Every 5 minutes
✅ Order Email Cron Job started successfully
   Thread is running in background
============================================================
✅ All cron jobs initialized successfully
============================================================
```

---

## ⚙️ Configuration Options

### Disable Cron Jobs (Development)

Set in `.env`:
```env
ENABLE_CRON_JOBS=false
```

### Change Schedule Interval

Edit `src/api/services/order_email_cron.py`:

```python
# Change from 5 minutes to 10 minutes
schedule.every(10).minutes.do(self.process_pending_order_emails)

# Or run every hour
schedule.every(1).hours.do(self.process_pending_order_emails)
```

### Customize Time Window

Edit the time threshold in `order_email_cron.py`:

```python
# Change from 10 minutes to 15 minutes
time_threshold = datetime.now() - timedelta(minutes=15)
```

---

## 🐛 Troubleshooting

### Emails Not Sending

1. **Check SMTP Configuration**
   ```bash
   # Verify environment variables
   echo $SMTP_HOST
   echo $SMTP_USERNAME
   ```

2. **Check Cron Job Status**
   - Look for startup logs in console
   - Check for error messages

3. **Verify Shop Owner Email**
   ```sql
   SELECT u.email, s.name
   FROM shops s
   JOIN users u ON s.owner_id = u.id
   WHERE s.id = YOUR_SHOP_ID;
   ```

4. **Test Email Service Directly**
   ```python
   from src.api.core.email_helper import EmailHelper
   helper = EmailHelper()
   success = helper._send_email_sync(
       to_email="test@example.com",
       subject="Test",
       html_content="<h1>Test</h1>"
   )
   print(success)
   ```

### Duplicate Emails

If shop owners receive duplicate emails:

1. Check order metadata is being saved
2. Verify time threshold logic
3. Check database connection persistence

### Missing Product Images

If product images don't show:

1. Verify product snapshot contains image data
2. Check image URL format
3. Use fallback placeholder image

---

## 📈 Future Improvements

### Recommended Enhancements

1. **Dedicated Email Tracking Table**
   ```sql
   CREATE TABLE order_email_logs (
       id SERIAL PRIMARY KEY,
       order_id INT,
       shop_id INT,
       email_sent_at TIMESTAMP,
       success BOOLEAN,
       error_message TEXT
   );
   ```

2. **Retry Logic**
   - Retry failed emails
   - Exponential backoff
   - Max retry attempts

3. **Email Templates in Database**
   - Store templates in `emailtemplate` table
   - Allow customization per shop
   - Version control for templates

4. **Email Queue System**
   - Use Celery or RQ for background tasks
   - Better scalability
   - More reliable delivery

5. **Email Analytics**
   - Track open rates
   - Track click rates
   - Shop owner engagement metrics

---

## 🎯 Production Deployment

### Recommendations

1. **Use Dedicated Email Service**
   - SendGrid
   - Amazon SES
   - Mailgun

2. **Monitor Cron Job**
   - Use logging service (e.g., Sentry)
   - Set up alerts for failures
   - Track success rates

3. **Scale Considerations**
   - For high volume, use message queue (Celery, RabbitMQ)
   - Consider batch processing
   - Implement rate limiting

4. **Backup Email Method**
   - Fallback SMTP server
   - Alternative notification (SMS, push)
   - Admin notification on failures

---

## 📝 Summary

Your order email cron job system is now fully set up and will:

✅ Run automatically every 5 minutes
✅ Send beautiful, responsive emails to shop owners
✅ Show only relevant products per shop
✅ Include product images and invoice details
✅ Prevent duplicate emails
✅ Log all activities
✅ Handle errors gracefully

**No manual intervention required!** The system runs in the background and keeps shop owners informed about new orders.

---

## 🆘 Support

If you encounter issues:

1. Check application logs
2. Verify environment variables
3. Test email configuration
4. Run manual test script
5. Check database for order data

For questions or assistance, refer to this documentation or contact your development team.

---

**Setup Date:** December 2, 2025
**Version:** 1.0
**Status:** ✅ Production Ready
