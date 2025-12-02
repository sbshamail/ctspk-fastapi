# Quick Start Guide - Order Email Cron Job

## ✅ Installation Complete!

The `schedule` module has been successfully installed. Your cron job system is ready to use!

---

## 🚀 Starting Your Application

Simply start your FastAPI application as normal:

```bash
uvicorn src.main:app --reload
```

Or if you use a different command:

```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

---

## 📋 What You'll See on Startup

When your application starts, you'll see output like this:

```
🟢 Application starting up...

============================================================
🚀 Initializing Cron Jobs
============================================================
🚀 Starting Order Email Cron Job
   Schedule: Every 5 minutes

============================================================
🔄 Order Email Cron Job Running at 2025-12-03 10:00:00
============================================================
📊 Found 0 orders to process
✅ No new orders to process

============================================================
✅ Cron job completed successfully
============================================================

✅ Order Email Cron Job started successfully
   Thread is running in background
============================================================
✅ All cron jobs initialized successfully
============================================================

INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

## 🧪 Manual Testing (Optional)

If you want to test the cron job immediately without waiting:

```bash
python -m src.api.services.order_email_cron
```

This will:
- Run the cron job once
- Show detailed logs
- Process any pending orders
- Send emails to shop owners

---

## 🔍 What the Cron Job Does

**Every 5 minutes**, it will:

1. ✅ Check for new orders (created in last 10 minutes)
2. ✅ Find orders that haven't had emails sent yet
3. ✅ For each order:
   - Get products grouped by shop
   - Send customized email to each shop owner
   - Show only their products with correct totals
4. ✅ Mark orders as "email sent" to prevent duplicates
5. ✅ Log everything for monitoring

---

## 📧 Example Email Sent

When Shop Owner receives the email:

**Subject:** New Order #TRK-ABC123 - Tech Store

**Email Contains:**
- Beautiful header with order number
- Order information (date, status, payment)
- **Only products from their shop** with images
- Shop-specific totals (subtotal, tax, discount, total)
- Customer information (name, email, phone)
- Shipping address
- "View Order Details" button
- Professional footer

---

## 🎯 Verifying It's Working

### Check Console Logs

Every 5 minutes, you'll see:

```
============================================================
🔄 Order Email Cron Job Running at 2025-12-03 10:05:00
============================================================
📊 Found 1 orders to process

📦 Processing Order #TRK-ABC123
   Order ID: 1
   Created: 2025-12-03 10:03:00
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

### Check Shop Owner Email

The shop owner should receive an email within 5 minutes of order placement.

---

## ⚙️ Configuration

### Disable Cron Jobs (Development)

If you want to disable cron jobs temporarily, add to `.env`:

```env
ENABLE_CRON_JOBS=false
```

Then restart your application.

### Change Schedule (Advanced)

To change from 5 minutes to a different interval, edit:

`src/api/services/order_email_cron.py` line 80:

```python
# Current: Every 5 minutes
schedule.every(5).minutes.do(self.process_pending_order_emails)

# Change to every 10 minutes:
schedule.every(10).minutes.do(self.process_pending_order_emails)

# Or every hour:
schedule.every(1).hours.do(self.process_pending_order_emails)
```

---

## 🐛 Troubleshooting

### "No module named 'schedule'"

Already fixed! The schedule module has been installed.

### No Emails Being Sent

1. **Check SMTP Settings** in `.env`:
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```

2. **Verify Shop Owner Has Email**:
   ```sql
   SELECT u.email, s.name
   FROM shops s
   JOIN users u ON s.owner_id = u.id;
   ```

3. **Check Logs** in console for error messages

4. **Test Email Helper**:
   ```bash
   python -c "from src.api.core.email_helper import EmailHelper; h = EmailHelper(); print('Email helper loaded')"
   ```

### Check Cron Job Status

Look for these logs when your app starts:
- ✅ "Starting Order Email Cron Job"
- ✅ "Order Email Cron Job started successfully"

If you see errors, check the error message.

---

## 📊 Monitoring

### View Logs in Real-Time

Your console will show cron job activity every 5 minutes. Watch for:
- Number of orders processed
- Number of emails sent
- Any error messages

### Check Order Metadata

Orders that have been processed will have metadata:

```python
order.metadata = {
    'shop_owner_email_sent': True,
    'shop_owner_email_sent_at': '2025-12-03T10:05:00'
}
```

---

## 🎉 You're Ready!

That's it! Your order email cron job is:

✅ **Installed** - Schedule module ready
✅ **Configured** - Cron job setup complete
✅ **Automatic** - Runs every 5 minutes
✅ **Smart** - Only sends to relevant shop owners
✅ **Beautiful** - Modern responsive email template
✅ **Safe** - Prevents duplicate emails

Just start your FastAPI app and it will work automatically! 🚀

---

## 📚 Need More Help?

- **Full Documentation**: See `ORDER_EMAIL_CRON_SETUP.md`
- **Email Template**: `src/api/templates/order_email_template.html`
- **Cron Job Code**: `src/api/services/order_email_cron.py`
- **Email Service**: `src/api/services/order_email_service.py`

---

**Setup Complete!** 🎊

Your shop owners will now receive beautiful order notification emails automatically!
