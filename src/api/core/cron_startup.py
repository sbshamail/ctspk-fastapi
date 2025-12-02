# src/api/core/cron_startup.py
"""
Cron job startup module
Initializes all cron jobs when the application starts
"""
import os
from src.api.services.order_email_cron import order_email_cron


def start_all_cron_jobs():
    """
    Start all cron jobs

    This function should be called during application startup
    """
    # Check if cron jobs should be enabled (useful for development)
    enable_cron = os.getenv('ENABLE_CRON_JOBS', 'true').lower() == 'true'

    if not enable_cron:
        print("⚠️  Cron jobs are disabled via ENABLE_CRON_JOBS environment variable")
        return

    print("\n" + "="*60)
    print("🚀 Initializing Cron Jobs")
    print("="*60)

    try:
        # Start order email cron job
        order_email_cron.start_cron_job()

        # Add more cron jobs here as needed
        # example_cron.start_cron_job()

        print("="*60)
        print("✅ All cron jobs initialized successfully")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Error starting cron jobs: {e}")
        import traceback
        traceback.print_exc()


def stop_all_cron_jobs():
    """
    Stop all cron jobs

    This function should be called during application shutdown
    """
    print("\n" + "="*60)
    print("🛑 Stopping Cron Jobs")
    print("="*60)

    try:
        # Stop order email cron job
        order_email_cron.stop_cron_job()

        # Add more cron job stops here as needed
        # example_cron.stop_cron_job()

        print("="*60)
        print("✅ All cron jobs stopped")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Error stopping cron jobs: {e}")
