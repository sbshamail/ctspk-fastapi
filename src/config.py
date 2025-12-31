import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        1440,
    )
)
DOMAIN = os.getenv("DOMAIN", "https://api.ctspk.com")

# =============================================================================
# Payment Gateway Configurations
# =============================================================================

# PayFast (Pakistan)
PAYFAST_MERCHANT_ID = os.getenv("PAYFAST_MERCHANT_ID")
PAYFAST_SECURED_KEY = os.getenv("PAYFAST_SECURED_KEY")
PAYFAST_BASE_URL = os.getenv("PAYFAST_BASE_URL", "https://ipguat.apps.net.pk")
PAYFAST_RETURN_URL = os.getenv("PAYFAST_RETURN_URL", f"{DOMAIN}/payment/callback/payfast")
PAYFAST_CANCEL_URL = os.getenv("PAYFAST_CANCEL_URL", f"{DOMAIN}/payment/cancel/payfast")

# EasyPaisa (Pakistan)
EASYPAISA_STORE_ID = os.getenv("EASYPAISA_STORE_ID")
EASYPAISA_HASH_KEY = os.getenv("EASYPAISA_HASH_KEY")
EASYPAISA_BASE_URL = os.getenv("EASYPAISA_BASE_URL", "https://easypay.easypaisa.com.pk")
EASYPAISA_RETURN_URL = os.getenv("EASYPAISA_RETURN_URL", f"{DOMAIN}/payment/callback/easypaisa")

# JazzCash (Pakistan)
JAZZCASH_MERCHANT_ID = os.getenv("JAZZCASH_MERCHANT_ID")
JAZZCASH_PASSWORD = os.getenv("JAZZCASH_PASSWORD")
JAZZCASH_INTEGRITY_SALT = os.getenv("JAZZCASH_INTEGRITY_SALT")
JAZZCASH_BASE_URL = os.getenv("JAZZCASH_BASE_URL", "https://sandbox.jazzcash.com.pk")
JAZZCASH_RETURN_URL = os.getenv("JAZZCASH_RETURN_URL", f"{DOMAIN}/payment/callback/jazzcash")

# PayPak (Pakistan Card Scheme)
PAYPAK_MERCHANT_ID = os.getenv("PAYPAK_MERCHANT_ID")
PAYPAK_API_KEY = os.getenv("PAYPAK_API_KEY")
PAYPAK_SECRET_KEY = os.getenv("PAYPAK_SECRET_KEY")
PAYPAK_BASE_URL = os.getenv("PAYPAK_BASE_URL", "https://api.paypak.pk")
PAYPAK_RETURN_URL = os.getenv("PAYPAK_RETURN_URL", f"{DOMAIN}/payment/callback/paypak")

# Stripe (International)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", f"{DOMAIN}/payment/callback/stripe")
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", f"{DOMAIN}/payment/cancel/stripe")
