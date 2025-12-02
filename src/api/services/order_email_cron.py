# src/api/services/order_email_cron.py
"""
Cron job service for sending order notification emails to shop owners
Runs every 5 minutes to check for new orders and send emails
"""
import schedule
import time
import threading
from datetime import datetime, timedelta
from sqlmodel import Session, select, and_
from typing import List

from src.lib.db_con import engine
from src.api.models.order_model.orderModel import Order, OrderProduct
from src.api.services.order_email_service import order_email_service


class OrderEmailCron:
    """Cron job for sending order emails to shop owners"""

    def __init__(self):
        self.is_running = False
        self.last_check_time = None

    def process_pending_order_emails(self):
        """
        Process orders that need email notifications sent to shop owners

        Logic:
        1. Find orders created in the last 10 minutes that haven't had emails sent
        2. For each order, send emails to all shop owners with products in the order
        3. Mark order as email sent (using order metadata or separate tracking)
        """
        print(f"\n{'='*60}")
        print(f"🔄 Order Email Cron Job Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        session = Session(engine)
        try:
            # Calculate time range (last 10 minutes to catch any missed)
            time_threshold = datetime.now() - timedelta(minutes=10)

            # Query for recent orders that need emails sent
            # We'll use a simple approach: find orders from last 10 minutes
            # In production, you'd want to track email_sent status in the database
            query = select(Order).where(
                and_(
                    Order.created_at >= time_threshold,
                    Order.order_status.in_(['order-pending', 'order-processing'])
                )
            ).order_by(Order.created_at.desc())

            orders = session.exec(query).all()

            print(f"📊 Found {len(orders)} orders to process")

            if not orders:
                print("✅ No new orders to process")
                return

            # Process each order
            for order in orders:
                print(f"\n📦 Processing Order #{order.tracking_number}")
                print(f"   Order ID: {order.id}")
                print(f"   Created: {order.created_at}")
                print(f"   Status: {order.order_status}")

                # Check if this order already has emails sent
                # You can implement tracking using order metadata or a separate table
                if self._has_email_been_sent(session, order):
                    print(f"   ⏭️  Email already sent for this order, skipping...")
                    continue

                # Get unique shop IDs from order products
                shop_ids = list(set([op.shop_id for op in order.order_products if op.shop_id]))
                print(f"   🏪 Shops involved: {len(shop_ids)}")

                # Send emails to all shop owners
                results = order_email_service.send_order_emails_to_all_shops(session, order)

                # Log results
                success_count = sum(1 for success in results.values() if success)
                print(f"   📧 Emails sent: {success_count}/{len(shop_ids)}")

                for shop_id, success in results.items():
                    status = "✅ Sent" if success else "❌ Failed"
                    print(f"      Shop {shop_id}: {status}")

                # Mark order as email sent
                if success_count > 0:
                    self._mark_email_as_sent(session, order)
                    print(f"   ✅ Order marked as email sent")

            session.commit()
            print(f"\n{'='*60}")
            print(f"✅ Cron job completed successfully")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"\n❌ Error in order email cron job: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()

    def _has_email_been_sent(self, session: Session, order: Order) -> bool:
        """
        Check if email has already been sent for this order

        This is a simple implementation using order metadata.
        In production, you might want a separate tracking table.
        """
        # Check if order has metadata indicating email was sent
        if hasattr(order, 'metadata') and order.metadata:
            if isinstance(order.metadata, dict):
                return order.metadata.get('shop_owner_email_sent', False)

        # For now, we'll assume orders older than 10 minutes have been processed
        # This prevents duplicate emails
        time_threshold = datetime.now() - timedelta(minutes=10)
        return order.created_at < time_threshold

    def _mark_email_as_sent(self, session: Session, order: Order):
        """
        Mark order as having email sent

        This is a simple implementation using order metadata.
        In production, you might want a separate tracking table.
        """
        try:
            # Update order metadata
            if not hasattr(order, 'metadata') or order.metadata is None:
                order.metadata = {}

            if isinstance(order.metadata, dict):
                order.metadata['shop_owner_email_sent'] = True
                order.metadata['shop_owner_email_sent_at'] = datetime.now().isoformat()

            session.add(order)
            session.flush()
        except Exception as e:
            print(f"Warning: Could not mark email as sent: {e}")
            # Don't fail the entire process if we can't update metadata

    def start_cron_job(self):
        """Start the cron job in a background thread"""
        if self.is_running:
            print("⚠️  Cron job is already running")
            return

        self.is_running = True
        print("🚀 Starting Order Email Cron Job")
        print("   Schedule: Every 5 minutes")

        # Schedule the job every 5 minutes
        schedule.every(5).minutes.do(self.process_pending_order_emails)

        # Run immediately on startup
        self.process_pending_order_emails()

        # Run scheduler in background thread
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds

        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()

        print("✅ Order Email Cron Job started successfully")
        print("   Thread is running in background")

    def stop_cron_job(self):
        """Stop the cron job"""
        self.is_running = False
        schedule.clear()
        print("🛑 Order Email Cron Job stopped")


# Create global instance
order_email_cron = OrderEmailCron()


# Entry point for manual execution
if __name__ == "__main__":
    print("=" * 60)
    print("Order Email Cron Job - Manual Execution")
    print("=" * 60)

    cron = OrderEmailCron()

    # Run once
    cron.process_pending_order_emails()

    print("\n" + "=" * 60)
    print("Manual execution completed")
    print("=" * 60)
