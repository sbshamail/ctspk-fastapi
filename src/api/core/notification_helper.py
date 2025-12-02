# notification_helper.py
"""
Centralized notification system for sending notifications to users
"""
from typing import Optional, List, Union
from sqlmodel import Session, select
from src.api.models.notificationModel import Notification
from src.api.models.usersModel import User
from src.api.models.shop_model.shopsModel import Shop
from datetime import datetime


class NotificationHelper:
    """Helper class for creating and sending notifications"""

    @staticmethod
    def create_notification(
        session: Session,
        user_id: int,
        message: str,
        commit: bool = True
    ) -> Optional[Notification]:
        """
        Create a notification for a user

        Args:
            session: Database session
            user_id: User ID to send notification to
            message: Notification message (supports limited HTML)
            commit: Whether to commit immediately (default: True)

        Returns:
            Notification instance or None if failed
        """
        try:
            notification = Notification(
                user_id=user_id,
                message=message,
                sent_at=datetime.utcnow(),
                is_read=False
            )
            session.add(notification)
            if commit:
                session.commit()
                session.refresh(notification)
            return notification
        except Exception as e:
            print(f"Error creating notification: {e}")
            return None

    @staticmethod
    def notify_multiple_users(
        session: Session,
        user_ids: List[int],
        message: str,
        commit: bool = True
    ) -> int:
        """
        Send same notification to multiple users

        Returns:
            Number of notifications created
        """
        count = 0
        for user_id in user_ids:
            if NotificationHelper.create_notification(session, user_id, message, commit=False):
                count += 1

        if commit:
            session.commit()

        return count

    # ============================================
    # USER REGISTRATION NOTIFICATIONS
    # ============================================

    @staticmethod
    def notify_user_registered(session: Session, user_id: int, user_name: str):
        """Notify user on successful registration"""
        message = f"<b>Welcome {user_name}!</b> Your account has been created successfully."
        NotificationHelper.create_notification(session, user_id, message)

    # ============================================
    # SHOP NOTIFICATIONS
    # ============================================

    @staticmethod
    def notify_shop_created(session: Session, shop_id: int, shop_name: str):
        """Notify shop owner and root users when shop is created"""
        shop = session.get(Shop, shop_id)
        if not shop:
            return

        # Notify shop owner
        owner_message = f"Your shop <b>{shop_name}</b> has been created and is pending approval."
        NotificationHelper.create_notification(session, shop.owner_id, owner_message)

        # Notify all root users
        root_users = session.exec(
            select(User).where(User.is_root == True)
        ).scalars().all()

        root_message = f"New shop <b>{shop_name}</b> has been created and requires approval."
        for root_user in root_users:
            NotificationHelper.create_notification(
                session, root_user.id, root_message, commit=False
            )
        session.commit()

    @staticmethod
    def notify_shop_approved(session: Session, shop_id: int):
        """Notify shop owner when shop is approved"""
        shop = session.get(Shop, shop_id)
        if not shop:
            return

        message = f"<b>Congratulations!</b> Your shop <b>{shop.name}</b> has been approved and is now active."
        NotificationHelper.create_notification(session, shop.owner_id, message)

    @staticmethod
    def notify_shop_disapproved(session: Session, shop_id: int, reason: Optional[str] = None):
        """Notify shop owner when shop is disapproved"""
        shop = session.get(Shop, shop_id)
        if not shop:
            return

        message = f"Your shop <b>{shop.name}</b> has been disapproved."
        if reason:
            message += f" Reason: {reason}"
        NotificationHelper.create_notification(session, shop.owner_id, message)

    # ============================================
    # PRODUCT STOCK NOTIFICATIONS
    # ============================================

    @staticmethod
    def notify_product_low_stock(
        session: Session,
        shop_id: int,
        product_name: str,
        current_stock: int,
        threshold: int = 10
    ):
        """Notify shop owner when product stock is low"""
        shop = session.get(Shop, shop_id)
        if not shop:
            return

        message = f"<b>Low Stock Alert!</b> Product <b>{product_name}</b> has only <b>{current_stock}</b> units left."
        NotificationHelper.create_notification(session, shop.owner_id, message)

    @staticmethod
    def notify_product_out_of_stock(session: Session, shop_id: int, product_name: str):
        """Notify shop owner when product is out of stock"""
        shop = session.get(Shop, shop_id)
        if not shop:
            return

        message = f"<b>Out of Stock!</b> Product <b>{product_name}</b> is now out of stock."
        NotificationHelper.create_notification(session, shop.owner_id, message)

    @staticmethod
    def notify_product_back_in_stock(session: Session, user_id: int, product_name: str):
        """Notify user when wishlisted product is back in stock"""
        message = f"<b>Good News!</b> Product <b>{product_name}</b> from your wishlist is back in stock!"
        NotificationHelper.create_notification(session, user_id, message)

    # ============================================
    # WISHLIST NOTIFICATIONS
    # ============================================

    @staticmethod
    def notify_wishlist_reminder(session: Session, user_id: int, product_name: str, days: int):
        """Remind user about product in wishlist (after 1 week)"""
        message = f"You added <b>{product_name}</b> to your wishlist {days} days ago. Still interested?"
        NotificationHelper.create_notification(session, user_id, message)

    # ============================================
    # CART NOTIFICATIONS
    # ============================================

    @staticmethod
    def notify_cart_reminder(session: Session, user_id: int, item_count: int):
        """Remind user about items in cart (after 2 days)"""
        message = f"You have <b>{item_count}</b> item(s) in your cart. Complete your purchase now!"
        NotificationHelper.create_notification(session, user_id, message)

    # ============================================
    # ORDER NOTIFICATIONS
    # ============================================

    @staticmethod
    def notify_order_placed(
        session: Session,
        order_id: int,
        tracking_number: str,
        customer_id: int,
        shop_ids: List[int],
        total_amount: float
    ):
        """Notify customer, shop owners, and admin when order is placed"""

        # Notify customer
        customer_message = f"Your order <b>{tracking_number}</b> has been placed successfully. Total: <b>${total_amount}</b>"
        NotificationHelper.create_notification(session, customer_id, customer_message)

        # Notify shop owners
        for shop_id in shop_ids:
            shop = session.get(Shop, shop_id)
            if shop:
                shop_message = f"New order <b>{tracking_number}</b> received for your shop <b>{shop.name}</b>."
                NotificationHelper.create_notification(
                    session, shop.owner_id, shop_message, commit=False
                )

        # Notify all root/admin users
        admin_users = session.exec(
            select(User).where(User.is_root == True)
        ).scalars().all()

        admin_message = f"New order <b>{tracking_number}</b> has been placed. Total: <b>${total_amount}</b>"
        for admin in admin_users:
            NotificationHelper.create_notification(
                session, admin.id, admin_message, commit=False
            )

        session.commit()

    @staticmethod
    def notify_order_status_changed(
        session: Session,
        order_id: int,
        tracking_number: str,
        customer_id: int,
        new_status: str
    ):
        """Notify customer when order status changes"""
        status_messages = {
            "processing": "is now being processed",
            "packed": "has been packed",
            "shipped": "has been shipped",
            "out_for_delivery": "is out for delivery",
            "at_local_facility": "has arrived at your local facility",
            "at_distribution_center": "is at the distribution center",
            "completed": "has been delivered successfully",
            "cancelled": "has been cancelled",
            "refunded": "has been refunded",
            "failed": "has failed"
        }

        status_text = status_messages.get(new_status.lower(), f"status changed to {new_status}")
        message = f"Your order <b>{tracking_number}</b> {status_text}."
        NotificationHelper.create_notification(session, customer_id, message)

    @staticmethod
    def notify_order_cancelled(
        session: Session,
        order_id: int,
        tracking_number: str,
        customer_id: int,
        shop_ids: List[int],
        cancelled_by: str = "customer"
    ):
        """Notify relevant parties when order is cancelled"""

        # Notify customer
        if cancelled_by == "admin":
            customer_message = f"Your order <b>{tracking_number}</b> has been cancelled by admin."
        else:
            customer_message = f"Your order <b>{tracking_number}</b> has been cancelled successfully."
        NotificationHelper.create_notification(session, customer_id, customer_message)

        # Notify shop owners
        for shop_id in shop_ids:
            shop = session.get(Shop, shop_id)
            if shop:
                shop_message = f"Order <b>{tracking_number}</b> for your shop has been cancelled."
                NotificationHelper.create_notification(
                    session, shop.owner_id, shop_message, commit=False
                )

        # Notify admins
        admin_users = session.exec(
            select(User).where(User.is_root == True)
        ).scalars().all()

        for admin in admin_users:
            admin_message = f"Order <b>{tracking_number}</b> has been cancelled by {cancelled_by}."
            NotificationHelper.create_notification(
                session, admin.id, admin_message, commit=False
            )

        session.commit()

    @staticmethod
    def notify_return_request_created(
        session: Session,
        return_id: int,
        order_tracking_number: str,
        customer_id: int,
        shop_ids: List[int]
    ):
        """Notify relevant parties when return request is created"""

        # Notify customer
        customer_message = f"Your return request for order <b>{order_tracking_number}</b> has been submitted successfully."
        NotificationHelper.create_notification(session, customer_id, customer_message)

        # Notify shop owners
        for shop_id in shop_ids:
            shop = session.get(Shop, shop_id)
            if shop:
                shop_message = f"New return request received for order <b>{order_tracking_number}</b>."
                NotificationHelper.create_notification(
                    session, shop.owner_id, shop_message, commit=False
                )

        # Notify admins
        admin_users = session.exec(
            select(User).where(User.is_root == True)
        ).scalars().all()

        for admin in admin_users:
            admin_message = f"New return request for order <b>{order_tracking_number}</b> requires review."
            NotificationHelper.create_notification(
                session, admin.id, admin_message, commit=False
            )

        session.commit()

    @staticmethod
    def notify_return_request_approved(
        session: Session,
        return_id: int,
        order_tracking_number: str,
        customer_id: int,
        shop_ids: List[int],
        refund_amount: float
    ):
        """Notify relevant parties when return request is approved"""

        # Notify customer
        customer_message = f"Your return request for order <b>{order_tracking_number}</b> has been approved. Refund amount: <b>${refund_amount}</b>"
        NotificationHelper.create_notification(session, customer_id, customer_message)

        # Notify shop owners
        for shop_id in shop_ids:
            shop = session.get(Shop, shop_id)
            if shop:
                shop_message = f"Return request for order <b>{order_tracking_number}</b> has been approved."
                NotificationHelper.create_notification(
                    session, shop.owner_id, shop_message, commit=False
                )

        session.commit()

    @staticmethod
    def notify_return_request_rejected(
        session: Session,
        return_id: int,
        order_tracking_number: str,
        customer_id: int,
        reason: Optional[str] = None
    ):
        """Notify customer when return request is rejected"""

        message = f"Your return request for order <b>{order_tracking_number}</b> has been rejected."
        if reason:
            message += f" Reason: {reason}"
        NotificationHelper.create_notification(session, customer_id, message)

    @staticmethod
    def notify_order_returned(
        session: Session,
        order_id: int,
        tracking_number: str,
        customer_id: int,
        shop_ids: List[int]
    ):
        """Notify relevant parties when order is returned/refunded"""

        # Notify customer
        customer_message = f"Your return request for order <b>{tracking_number}</b> has been processed."
        NotificationHelper.create_notification(session, customer_id, customer_message)

        # Notify shop owners
        for shop_id in shop_ids:
            shop = session.get(Shop, shop_id)
            if shop:
                shop_message = f"Order <b>{tracking_number}</b> has been returned."
                NotificationHelper.create_notification(
                    session, shop.owner_id, shop_message, commit=False
                )

        # Notify admins
        admin_users = session.exec(
            select(User).where(User.is_root == True)
        ).scalars().all()

        for admin in admin_users:
            admin_message = f"Order <b>{tracking_number}</b> has been returned/refunded."
            NotificationHelper.create_notification(
                session, admin.id, admin_message, commit=False
            )

        session.commit()

    @staticmethod
    def notify_order_assigned_to_fulfillment(
        session: Session,
        order_id: int,
        tracking_number: str,
        customer_id: int,
        fulfillment_user_id: int
    ):
        """Notify fulfillment user and customer when order is assigned"""

        # Notify fulfillment user
        fulfillment_message = f"Order <b>{tracking_number}</b> has been assigned to you for fulfillment."
        NotificationHelper.create_notification(session, fulfillment_user_id, fulfillment_message)

        # Notify customer
        customer_message = f"Your order <b>{tracking_number}</b> has been assigned for delivery."
        NotificationHelper.create_notification(session, customer_id, customer_message)

    # ============================================
    # WITHDRAWAL NOTIFICATIONS
    # ============================================

    @staticmethod
    def notify_withdrawal_requested(
        session: Session,
        shop_id: int,
        amount: float,
        request_id: int
    ):
        """Notify shop owner and admin when withdrawal is requested"""
        shop = session.get(Shop, shop_id)
        if not shop:
            return

        # Notify shop owner
        owner_message = f"Your withdrawal request for <b>${amount}</b> has been submitted and is pending approval."
        NotificationHelper.create_notification(session, shop.owner_id, owner_message)

        # Notify admins
        admin_users = session.exec(
            select(User).where(User.is_root == True)
        ).scalars().all()

        for admin in admin_users:
            admin_message = f"New withdrawal request from shop <b>{shop.name}</b> for <b>${amount}</b>."
            NotificationHelper.create_notification(
                session, admin.id, admin_message, commit=False
            )

        session.commit()

    @staticmethod
    def notify_withdrawal_approved(session: Session, shop_id: int, amount: float):
        """Notify shop owner when withdrawal is approved"""
        shop = session.get(Shop, shop_id)
        if not shop:
            return

        message = f"<b>Great News!</b> Your withdrawal request for <b>${amount}</b> has been approved."
        NotificationHelper.create_notification(session, shop.owner_id, message)

    @staticmethod
    def notify_withdrawal_rejected(
        session: Session,
        shop_id: int,
        amount: float,
        reason: Optional[str] = None
    ):
        """Notify shop owner when withdrawal is rejected"""
        shop = session.get(Shop, shop_id)
        if not shop:
            return

        message = f"Your withdrawal request for <b>${amount}</b> has been rejected."
        if reason:
            message += f" Reason: {reason}"
        NotificationHelper.create_notification(session, shop.owner_id, message)

    @staticmethod
    def notify_withdrawal_processed(session: Session, shop_id: int, amount: float, net_amount: float):
        """Notify shop owner when withdrawal is processed (money transferred)"""
        shop = session.get(Shop, shop_id)
        if not shop:
            return

        message = f"<b>Payment Completed!</b> Your withdrawal of <b>${net_amount}</b> has been processed and transferred to your account."
        NotificationHelper.create_notification(session, shop.owner_id, message)


# Create global instance
notification_helper = NotificationHelper()


# Convenience functions for easy import
def notify_user_registered(session: Session, user_id: int, user_name: str):
    """Shortcut: Notify user on registration"""
    return notification_helper.notify_user_registered(session, user_id, user_name)


def notify_shop_created(session: Session, shop_id: int, shop_name: str):
    """Shortcut: Notify on shop creation"""
    return notification_helper.notify_shop_created(session, shop_id, shop_name)


def notify_order_placed(session: Session, order_id: int, tracking_number: str,
                       customer_id: int, shop_ids: List[int], total_amount: float):
    """Shortcut: Notify on order placement"""
    return notification_helper.notify_order_placed(
        session, order_id, tracking_number, customer_id, shop_ids, total_amount
    )


def notify_withdrawal_requested(session: Session, shop_id: int, amount: float, request_id: int):
    """Shortcut: Notify on withdrawal request"""
    return notification_helper.notify_withdrawal_requested(session, shop_id, amount, request_id)
