# notification_tasks.py
"""
Background tasks for scheduled notifications and emails (wishlist/cart reminders, stock alerts)
These should be run as cron jobs or scheduled tasks
"""
from datetime import datetime, timedelta
from sqlmodel import Session, select
from src.lib.db_con import engine
from src.api.models.wishlistModel import Wishlist
from src.api.models.cartModel import Cart
from src.api.models.productModel import Product
from src.api.core.notification_helper import notification_helper
from src.api.core.email_notification_helper import email_notification_helper


def send_wishlist_reminders():
    """
    Send reminders (notification + email) for wishlist items added more than 7 days ago
    Run this daily via cron job
    """
    print("🔔 Running wishlist reminder task...")

    with Session(engine) as session:
        # Get wishlist items older than 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        wishlist_items = session.exec(
            select(Wishlist).where(
                Wishlist.created_at <= seven_days_ago
            )
        ).scalars().all()

        notification_count = 0
        email_count = 0

        for item in wishlist_items:
            try:
                product = session.get(Product, item.product_id)
                if product:
                    days_in_wishlist = (datetime.utcnow() - item.created_at).days

                    # Send in-app notification
                    notification_helper.notify_wishlist_reminder(
                        session,
                        item.user_id,
                        product.name,
                        days_in_wishlist
                    )
                    notification_count += 1

                    # Send email
                    email_notification_helper.send_wishlist_reminder_email(
                        session,
                        item.user_id,
                        product.name,
                        product.id,
                        days_in_wishlist,
                        product_url=f"/product/{product.slug or product.id}"
                    )
                    email_count += 1

            except Exception as e:
                print(f"❌ Error sending wishlist reminder: {e}")

        print(f"✅ Sent {notification_count} wishlist notifications and {email_count} emails")


def send_cart_reminders():
    """
    Send reminders (notification + email) for cart items added more than 2 days ago
    Run this daily via cron job
    """
    print("🔔 Running cart reminder task...")

    with Session(engine) as session:
        # Get cart items older than 2 days, group by user
        two_days_ago = datetime.utcnow() - timedelta(days=2)

        # Get distinct users with old cart items
        cart_items = session.exec(
            select(Cart).where(
                Cart.created_at <= two_days_ago
            )
        ).scalars().all()

        # Group by user_id and calculate total
        user_cart_data = {}
        for item in cart_items:
            if item.user_id not in user_cart_data:
                user_cart_data[item.user_id] = {
                    'count': 0,
                    'total': 0.0
                }
            user_cart_data[item.user_id]['count'] += 1
            # Calculate item total (price * quantity)
            if hasattr(item, 'price') and hasattr(item, 'quantity'):
                user_cart_data[item.user_id]['total'] += float(item.price * item.quantity)

        # Send one notification + email per user
        notification_count = 0
        email_count = 0

        for user_id, data in user_cart_data.items():
            try:
                # Send in-app notification
                notification_helper.notify_cart_reminder(
                    session,
                    user_id,
                    data['count']
                )
                notification_count += 1

                # Send email
                email_notification_helper.send_cart_reminder_email(
                    session,
                    user_id,
                    data['count'],
                    data['total'] if data['total'] > 0 else None
                )
                email_count += 1

            except Exception as e:
                print(f"❌ Error sending cart reminder: {e}")

        print(f"✅ Sent {notification_count} cart notifications and {email_count} emails")


def check_low_stock_products():
    """
    Check for low stock products and notify shop owners (notification + email)
    Run this daily via cron job
    """
    print("🔔 Running low stock check...")

    with Session(engine) as session:
        # Get products with low stock (less than 10 units)
        LOW_STOCK_THRESHOLD = 10

        low_stock_products = session.exec(
            select(Product).where(
                Product.quantity > 0,
                Product.quantity <= LOW_STOCK_THRESHOLD
            )
        ).scalars().all()

        notification_count = 0
        email_count = 0

        for product in low_stock_products:
            try:
                if product.shop_id:
                    # Send in-app notification
                    notification_helper.notify_product_low_stock(
                        session,
                        product.shop_id,
                        product.name,
                        product.quantity,
                        LOW_STOCK_THRESHOLD
                    )
                    notification_count += 1

                    # Send email
                    email_notification_helper.send_low_stock_email(
                        session,
                        product.shop_id,
                        product.name,
                        product.id,
                        product.quantity,
                        LOW_STOCK_THRESHOLD
                    )
                    email_count += 1

            except Exception as e:
                print(f"❌ Error sending low stock alert: {e}")

        print(f"✅ Sent {notification_count} low stock notifications and {email_count} emails")


def check_out_of_stock_products():
    """
    Check for out of stock products and notify shop owners (notification + email)
    Run this when products go out of stock (or daily)
    """
    print("🔔 Running out of stock check...")

    with Session(engine) as session:
        # Get products that are out of stock
        out_of_stock_products = session.exec(
            select(Product).where(
                Product.quantity == 0
            )
        ).scalars().all()

        notification_count = 0
        email_count = 0

        for product in out_of_stock_products:
            try:
                if product.shop_id:
                    # Send in-app notification
                    notification_helper.notify_product_out_of_stock(
                        session,
                        product.shop_id,
                        product.name
                    )
                    notification_count += 1

                    # Send email
                    email_notification_helper.send_out_of_stock_email(
                        session,
                        product.shop_id,
                        product.name,
                        product.id
                    )
                    email_count += 1

            except Exception as e:
                print(f"❌ Error sending out of stock alert: {e}")

        print(f"✅ Sent {notification_count} out of stock notifications and {email_count} emails")


if __name__ == "__main__":
    """
    Run all scheduled tasks
    Set up a cron job to run this script daily:

    Linux/Mac:
    0 9 * * * cd /path/to/project && python -m src.api.core.notification_tasks

    Windows Task Scheduler:
    python C:\ctspk-fastapi\src\api\core\notification_tasks.py
    """
    print("=" * 60)
    print("Starting Notification Background Tasks")
    print("=" * 60)

    send_wishlist_reminders()
    send_cart_reminders()
    check_low_stock_products()
    check_out_of_stock_products()

    print("=" * 60)
    print("All notification tasks completed!")
    print("=" * 60)
