import json
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple

from src.config import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    STRIPE_SUCCESS_URL,
    STRIPE_CANCEL_URL,
)
from ..base_gateway import (
    BasePaymentGateway,
    PaymentInitiationResult,
    PaymentVerificationResult,
    RefundResult,
    WebhookVerificationResult,
)

# Stripe import with fallback
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None


class StripeGateway(BasePaymentGateway):
    """Stripe International Payment Gateway"""

    def __init__(self):
        super().__init__()
        self.gateway_name = "stripe"
        self.flow_type = "redirect"
        self.currency = "USD"
        self.supports_refund = True
        self.supports_partial_refund = True

        self.secret_key = STRIPE_SECRET_KEY
        self.webhook_secret = STRIPE_WEBHOOK_SECRET
        self.success_url = STRIPE_SUCCESS_URL
        self.cancel_url = STRIPE_CANCEL_URL

        if STRIPE_AVAILABLE and self.secret_key:
            stripe.api_key = self.secret_key

    def initialize(self) -> bool:
        """Verify Stripe configuration"""
        return STRIPE_AVAILABLE and bool(self.secret_key)

    def initiate_payment(
        self,
        transaction_id: str,
        amount: Decimal,
        order_id: int,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentInitiationResult:
        """Create Stripe Checkout Session"""
        if not STRIPE_AVAILABLE:
            return PaymentInitiationResult(
                success=False,
                transaction_id=transaction_id,
                error_message="Stripe library not installed",
            )

        try:
            amount_cents = int(amount * 100)

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": self.currency.lower(),
                            "product_data": {
                                "name": description or f"Order #{order_id}",
                            },
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=f"{self.success_url}?session_id={{CHECKOUT_SESSION_ID}}&token={transaction_id}",
                cancel_url=f"{self.cancel_url}?token={transaction_id}",
                customer_email=customer_email if customer_email else None,
                metadata={
                    "transaction_id": transaction_id,
                    "order_id": str(order_id),
                    **(metadata or {}),
                },
            )

            return PaymentInitiationResult(
                success=True,
                transaction_id=transaction_id,
                gateway_transaction_id=session.id,
                redirect_url=session.url,
                payment_data={"session_id": session.id},
            )

        except stripe.error.StripeError as e:
            return PaymentInitiationResult(
                success=False,
                transaction_id=transaction_id,
                error_code=getattr(e, "code", None),
                error_message=str(e),
            )
        except Exception as e:
            return PaymentInitiationResult(
                success=False,
                transaction_id=transaction_id,
                error_message=str(e),
            )

    def verify_payment(
        self,
        transaction_id: str,
        gateway_transaction_id: Optional[str] = None,
        verification_data: Optional[Dict[str, Any]] = None,
    ) -> PaymentVerificationResult:
        """Verify Stripe payment via Checkout Session"""
        if not STRIPE_AVAILABLE:
            return PaymentVerificationResult(
                success=False,
                status="error",
                error_message="Stripe library not installed",
            )

        try:
            session_id = gateway_transaction_id
            if verification_data and "session_id" in verification_data:
                session_id = verification_data["session_id"]

            if not session_id:
                return PaymentVerificationResult(
                    success=False,
                    status="error",
                    error_message="Session ID not provided",
                )

            session = stripe.checkout.Session.retrieve(session_id)

            status = "pending"
            if session.payment_status == "paid":
                status = "completed"
            elif session.payment_status == "unpaid":
                status = "pending"
            else:
                status = "failed"

            return PaymentVerificationResult(
                success=status == "completed",
                status=status,
                gateway_transaction_id=session.payment_intent,
                amount=Decimal(session.amount_total or 0) / 100,
                gateway_response=dict(session),
            )

        except stripe.error.StripeError as e:
            return PaymentVerificationResult(
                success=False,
                status="error",
                error_code=getattr(e, "code", None),
                error_message=str(e),
            )
        except Exception as e:
            return PaymentVerificationResult(
                success=False,
                status="error",
                error_message=str(e),
            )

    def process_callback(
        self, callback_data: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Process Stripe callback (success/cancel redirect)"""
        session_id = callback_data.get("session_id")
        transaction_id = callback_data.get("token", "")

        if session_id:
            result = self.verify_payment(
                transaction_id, session_id, {"session_id": session_id}
            )
            return result.success, transaction_id, callback_data

        return False, transaction_id, callback_data

    def verify_webhook(
        self, payload: bytes, headers: Dict[str, str]
    ) -> WebhookVerificationResult:
        """Verify Stripe webhook signature"""
        if not STRIPE_AVAILABLE:
            return WebhookVerificationResult(
                valid=False, error_message="Stripe library not installed"
            )

        try:
            sig_header = headers.get("stripe-signature") or headers.get(
                "Stripe-Signature", ""
            )

            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )

            if event["type"] == "checkout.session.completed":
                session = event["data"]["object"]
                transaction_id = session.get("metadata", {}).get("transaction_id")
                status = (
                    "completed"
                    if session.get("payment_status") == "paid"
                    else "pending"
                )

                return WebhookVerificationResult(
                    valid=True,
                    transaction_id=transaction_id,
                    status=status,
                    parsed_data=dict(session),
                )

            elif event["type"] == "payment_intent.payment_failed":
                payment_intent = event["data"]["object"]
                transaction_id = payment_intent.get("metadata", {}).get(
                    "transaction_id"
                )

                return WebhookVerificationResult(
                    valid=True,
                    transaction_id=transaction_id,
                    status="failed",
                    parsed_data=dict(payment_intent),
                )

            return WebhookVerificationResult(valid=True, parsed_data=dict(event))

        except stripe.error.SignatureVerificationError as e:
            return WebhookVerificationResult(
                valid=False, error_message=f"Invalid signature: {str(e)}"
            )
        except Exception as e:
            return WebhookVerificationResult(valid=False, error_message=str(e))

    def refund(
        self,
        transaction_id: str,
        gateway_transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> RefundResult:
        """Process Stripe refund"""
        if not STRIPE_AVAILABLE:
            return RefundResult(
                success=False, error_message="Stripe library not installed"
            )

        try:
            refund_params = {
                "payment_intent": gateway_transaction_id,
            }

            if amount:
                refund_params["amount"] = int(amount * 100)

            if reason:
                refund_params["reason"] = reason

            refund = stripe.Refund.create(**refund_params)

            return RefundResult(
                success=refund.status == "succeeded",
                refund_id=refund.id,
                refunded_amount=Decimal(refund.amount) / 100,
                status=refund.status,
            )

        except stripe.error.StripeError as e:
            return RefundResult(
                success=False,
                error_code=getattr(e, "code", None),
                error_message=str(e),
            )
        except Exception as e:
            return RefundResult(success=False, error_message=str(e))

    def get_transaction_status(
        self, transaction_id: str, gateway_transaction_id: Optional[str] = None
    ) -> PaymentVerificationResult:
        """Get Stripe payment status"""
        if not STRIPE_AVAILABLE:
            return PaymentVerificationResult(
                success=False,
                status="error",
                error_message="Stripe library not installed",
            )

        try:
            if gateway_transaction_id and gateway_transaction_id.startswith("pi_"):
                payment_intent = stripe.PaymentIntent.retrieve(gateway_transaction_id)

                status_map = {
                    "succeeded": "completed",
                    "processing": "processing",
                    "requires_payment_method": "pending",
                    "canceled": "cancelled",
                }

                return PaymentVerificationResult(
                    success=payment_intent.status == "succeeded",
                    status=status_map.get(payment_intent.status, "pending"),
                    gateway_transaction_id=payment_intent.id,
                    amount=Decimal(payment_intent.amount) / 100,
                    gateway_response=dict(payment_intent),
                )

            return self.verify_payment(transaction_id, gateway_transaction_id)

        except stripe.error.StripeError as e:
            return PaymentVerificationResult(
                success=False,
                status="error",
                error_code=getattr(e, "code", None),
                error_message=str(e),
            )
        except Exception as e:
            return PaymentVerificationResult(
                success=False,
                status="error",
                error_message=str(e),
            )
