# email_notification_helper.py
"""
Email notification system for automated reminders and alerts
Works alongside the notification system to send emails
"""
from typing import List, Optional
from sqlmodel import Session, select
from src.api.models.usersModel import User
from src.api.models.shopModel import Shop
from src.api.core.email_helper import send_email


class EmailNotificationHelper:
    """Helper class for sending automated email notifications"""

    # Email Template IDs (update these based on your actual template IDs)
    TEMPLATE_WISHLIST_REMINDER = 10
    TEMPLATE_CART_REMINDER = 11
    TEMPLATE_LOW_STOCK = 12
    TEMPLATE_OUT_OF_STOCK = 13
    TEMPLATE_BACK_IN_STOCK = 14
    TEMPLATE_ORDER_PLACED = 15
    TEMPLATE_ORDER_STATUS_CHANGED = 16
    TEMPLATE_WITHDRAWAL_REQUESTED = 17
    TEMPLATE_WITHDRAWAL_APPROVED = 18

    @staticmethod
    def get_user_email(session: Session, user_id: int) -> Optional[str]:
        """Get user email from database"""
        user = session.get(User, user_id)
        return user.email if user else None

    @staticmethod
    def get_shop_owner_email(session: Session, shop_id: int) -> Optional[str]:
        """Get shop owner email"""
        shop = session.get(Shop, shop_id)
        if shop:
            owner = session.get(User, shop.owner_id)
            return owner.email if owner else None
        return None

    @staticmethod
    def get_admin_emails(session: Session) -> List[str]:
        """Get all admin/root user emails"""
        admin_users = session.exec(
            select(User).where(User.is_root == True)
        ).scalars().all()
        return [admin.email for admin in admin_users if admin.email]

    # ============================================
    # WISHLIST REMINDERS
    # ============================================

    @staticmethod
    def send_wishlist_reminder_email(
        session: Session,
        user_id: int,
        product_name: str,
        product_id: int,
        days: int,
        product_url: Optional[str] = None
    ):
        """
        Send wishlist reminder email to user

        Args:
            session: Database session
            user_id: User ID
            product_name: Name of the product
            product_id: Product ID
            days: Number of days in wishlist
            product_url: Optional URL to product page
        """
        user_email = EmailNotificationHelper.get_user_email(session, user_id)
        if not user_email:
            print(f"No email found for user {user_id}")
            return

        user = session.get(User, user_id)
        if not user:
            return

        replacements = {
            "user_name": user.name or "Customer",
            "product_name": product_name,
            "product_id": product_id,
            "days": days,
            "product_url": product_url or f"/product/{product_id}",
            "view_product_link": product_url or f"/product/{product_id}",
            "wishlist_url": "/wishlist"
        }

        try:
            send_email(
                to_email=user_email,
                email_template_id=EmailNotificationHelper.TEMPLATE_WISHLIST_REMINDER,
                replacements=replacements,
                session=session
            )
            print(f"✅ Wishlist reminder email sent to {user_email}")
        except Exception as e:
            print(f"❌ Error sending wishlist reminder email: {e}")

    # ============================================
    # CART REMINDERS
    # ============================================

    @staticmethod
    def send_cart_reminder_email(
        session: Session,
        user_id: int,
        item_count: int,
        total_amount: Optional[float] = None
    ):
        """
        Send cart reminder email to user

        Args:
            session: Database session
            user_id: User ID
            item_count: Number of items in cart
            total_amount: Optional total cart value
        """
        user_email = EmailNotificationHelper.get_user_email(session, user_id)
        if not user_email:
            print(f"No email found for user {user_id}")
            return

        user = session.get(User, user_id)
        if not user:
            return

        replacements = {
            "user_name": user.name or "Customer",
            "item_count": item_count,
            "total_amount": f"Rs.{total_amount:.2f}" if total_amount else "N/A",
            "cart_url": "/cart",
            "checkout_url": "/checkout"
        }

        try:
            send_email(
                to_email=user_email,
                email_template_id=EmailNotificationHelper.TEMPLATE_CART_REMINDER,
                replacements=replacements,
                session=session
            )
            print(f"✅ Cart reminder email sent to {user_email}")
        except Exception as e:
            print(f"❌ Error sending cart reminder email: {e}")

    # ============================================
    # STOCK ALERTS
    # ============================================

    @staticmethod
    def send_low_stock_email(
        session: Session,
        shop_id: int,
        product_name: str,
        product_id: int,
        current_stock: int,
        threshold: int = 10
    ):
        """
        Send low stock alert email to shop owner

        Args:
            session: Database session
            shop_id: Shop ID
            product_name: Product name
            product_id: Product ID
            current_stock: Current stock level
            threshold: Low stock threshold
        """
        shop_owner_email = EmailNotificationHelper.get_shop_owner_email(session, shop_id)
        if not shop_owner_email:
            print(f"No email found for shop {shop_id}")
            return

        shop = session.get(Shop, shop_id)
        if not shop:
            return

        owner = session.get(User, shop.owner_id)
        if not owner:
            return

        replacements = {
            "shop_name": shop.name,
            "owner_name": owner.name or "Shop Owner",
            "product_name": product_name,
            "product_id": product_id,
            "current_stock": current_stock,
            "threshold": threshold,
            "product_url": f"/admin/products/{product_id}",
            "inventory_url": "/admin/inventory"
        }

        try:
            send_email(
                to_email=shop_owner_email,
                email_template_id=EmailNotificationHelper.TEMPLATE_LOW_STOCK,
                replacements=replacements,
                session=session
            )
            print(f"✅ Low stock email sent to {shop_owner_email}")
        except Exception as e:
            print(f"❌ Error sending low stock email: {e}")

    @staticmethod
    def send_out_of_stock_email(
        session: Session,
        shop_id: int,
        product_name: str,
        product_id: int
    ):
        """
        Send out of stock alert email to shop owner

        Args:
            session: Database session
            shop_id: Shop ID
            product_name: Product name
            product_id: Product ID
        """
        shop_owner_email = EmailNotificationHelper.get_shop_owner_email(session, shop_id)
        if not shop_owner_email:
            print(f"No email found for shop {shop_id}")
            return

        shop = session.get(Shop, shop_id)
        if not shop:
            return

        owner = session.get(User, shop.owner_id)
        if not owner:
            return

        replacements = {
            "shop_name": shop.name,
            "owner_name": owner.name or "Shop Owner",
            "product_name": product_name,
            "product_id": product_id,
            "product_url": f"/admin/products/{product_id}",
            "restock_url": f"/admin/products/{product_id}/restock"
        }

        try:
            send_email(
                to_email=shop_owner_email,
                email_template_id=EmailNotificationHelper.TEMPLATE_OUT_OF_STOCK,
                replacements=replacements,
                session=session
            )
            print(f"✅ Out of stock email sent to {shop_owner_email}")
        except Exception as e:
            print(f"❌ Error sending out of stock email: {e}")

    @staticmethod
    def send_back_in_stock_email(
        session: Session,
        user_id: int,
        product_name: str,
        product_id: int,
        product_url: Optional[str] = None
    ):
        """
        Send back in stock email to user who wishlisted the product

        Args:
            session: Database session
            user_id: User ID
            product_name: Product name
            product_id: Product ID
            product_url: Optional product URL
        """
        user_email = EmailNotificationHelper.get_user_email(session, user_id)
        if not user_email:
            print(f"No email found for user {user_id}")
            return

        user = session.get(User, user_id)
        if not user:
            return

        replacements = {
            "user_name": user.name or "Customer",
            "product_name": product_name,
            "product_id": product_id,
            "product_url": product_url or f"/product/{product_id}",
            "shop_now_link": product_url or f"/product/{product_id}"
        }

        try:
            send_email(
                to_email=user_email,
                email_template_id=EmailNotificationHelper.TEMPLATE_BACK_IN_STOCK,
                replacements=replacements,
                session=session
            )
            print(f"✅ Back in stock email sent to {user_email}")
        except Exception as e:
            print(f"❌ Error sending back in stock email: {e}")


# Create global instance
email_notification_helper = EmailNotificationHelper()


# Convenience functions
def send_wishlist_reminder_email(session: Session, user_id: int, product_name: str,
                                product_id: int, days: int, product_url: Optional[str] = None):
    """Shortcut: Send wishlist reminder email"""
    return email_notification_helper.send_wishlist_reminder_email(
        session, user_id, product_name, product_id, days, product_url
    )


def send_cart_reminder_email(session: Session, user_id: int, item_count: int,
                            total_amount: Optional[float] = None):
    """Shortcut: Send cart reminder email"""
    return email_notification_helper.send_cart_reminder_email(
        session, user_id, item_count, total_amount
    )


def send_low_stock_email(session: Session, shop_id: int, product_name: str,
                        product_id: int, current_stock: int, threshold: int = 10):
    """Shortcut: Send low stock email"""
    return email_notification_helper.send_low_stock_email(
        session, shop_id, product_name, product_id, current_stock, threshold
    )


def send_out_of_stock_email(session: Session, shop_id: int, product_name: str, product_id: int):
    """Shortcut: Send out of stock email"""
    return email_notification_helper.send_out_of_stock_email(
        session, shop_id, product_name, product_id
    )


def send_back_in_stock_email(session: Session, user_id: int, product_name: str,
                            product_id: int, product_url: Optional[str] = None):
    """Shortcut: Send back in stock email"""
    return email_notification_helper.send_back_in_stock_email(
        session, user_id, product_name, product_id, product_url
    )
