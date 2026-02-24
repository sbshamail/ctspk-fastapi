# src/api/services/order_email_cron.py
"""
Cron job: sends order notification emails every 5 minutes.
Two emails per new order:
  1. Shop-owner invoice  — per shop, showing only that shop's products.
  2. Admin invoice       — sent to all is_root users, full order with all shops.
"""
import schedule
import time
import threading
from datetime import datetime, timedelta
from sqlmodel import Session, select, and_

from src.lib.db_con import engine
from src.api.models.order_model.orderModel import Order
from src.api.services.order_email_service import order_email_service


class OrderEmailCron:
    """Cron job for sending order emails to shop owners and admin users."""

    def __init__(self):
        self.is_running = False

    def process_pending_order_emails(self):
        """
        Find orders created in the last 10 minutes with pending/processing status
        and send shop-owner + admin emails for any that haven't been emailed yet.
        """
        print(f"\n{'='*60}")
        print(f"[order-email] cron running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        session = Session(engine)
        try:
            time_threshold = datetime.now() - timedelta(minutes=10)

            orders = session.exec(
                select(Order).where(
                    and_(
                        Order.created_at >= time_threshold,
                        Order.order_status.in_(['order-pending', 'order-processing',
                                                'pending', 'processing'])
                    )
                ).order_by(Order.created_at.desc())
            ).all()

            print(f"[order-email] {len(orders)} order(s) in window")

            if not orders:
                print("[order-email] nothing to process")
                return

            for order in orders:
                print(f"\n[order-email] processing order #{order.tracking_number} (id={order.id})")

                if self._email_already_sent(order):
                    print(f"[order-email] already sent for #{order.tracking_number}, skipping")
                    continue

                shop_ids = list({op.shop_id for op in order.order_products if op.shop_id})
                print(f"[order-email] {len(shop_ids)} shop(s) in order")

                # 1. Shop-owner emails
                shop_results = order_email_service.send_order_emails_to_all_shops(session, order)
                shop_ok = sum(1 for v in shop_results.values() if v)
                print(f"[order-email] shop-owner emails: {shop_ok}/{len(shop_ids)} sent")

                # 2. Admin email
                admin_ok = order_email_service.send_admin_email(session, order)
                print(f"[order-email] admin email: {'sent' if admin_ok else 'failed/skipped'}")

                # Mark as sent if at least one email succeeded
                if shop_ok > 0 or admin_ok:
                    self._mark_email_sent(session, order)

            session.commit()
            print(f"\n[order-email] cron complete")

        except Exception as e:
            print(f"[order-email] ERROR: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()

    # ─── Duplicate-prevention helpers ──────────────────────────────────────

    def _email_already_sent(self, order: Order) -> bool:
        """Return True if both shop-owner and admin emails have been sent."""
        if hasattr(order, 'metadata') and isinstance(order.metadata, dict):
            return order.metadata.get('order_email_sent', False)
        # Fallback: treat orders older than 10 min as already processed
        return order.created_at < (datetime.now() - timedelta(minutes=10))

    def _mark_email_sent(self, session: Session, order: Order):
        """Record in order metadata that emails have been sent."""
        try:
            meta = order.metadata if isinstance(getattr(order, 'metadata', None), dict) else {}
            meta['order_email_sent'] = True
            meta['order_email_sent_at'] = datetime.now().isoformat()
            order.metadata = meta
            session.add(order)
            session.flush()
        except Exception as e:
            print(f"[order-email] warning: could not mark email sent: {e}")

    # ─── Scheduler lifecycle ───────────────────────────────────────────────

    def start_cron_job(self):
        """Start the cron job in a background daemon thread."""
        if self.is_running:
            print("[order-email] cron already running")
            return

        self.is_running = True
        print("[order-email] starting cron job (every 5 minutes)")

        schedule.every(5).minutes.do(self.process_pending_order_emails)

        # Run once immediately on startup
        self.process_pending_order_emails()

        def _run():
            while self.is_running:
                schedule.run_pending()
                time.sleep(30)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        print("[order-email] background thread started")

    def stop_cron_job(self):
        """Stop the scheduler."""
        self.is_running = False
        schedule.clear()
        print("[order-email] cron stopped")


# Global instance used by cron_startup.py
order_email_cron = OrderEmailCron()


if __name__ == "__main__":
    print("=" * 60)
    print("Order Email Cron — Manual Run")
    print("=" * 60)
    OrderEmailCron().process_pending_order_emails()
