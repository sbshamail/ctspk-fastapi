import hashlib
import hmac
import json
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
import httpx

from src.config import (
    PAYPAK_MERCHANT_ID,
    PAYPAK_API_KEY,
    PAYPAK_SECRET_KEY,
    PAYPAK_BASE_URL,
    PAYPAK_RETURN_URL,
)
from ..base_gateway import (
    BasePaymentGateway,
    PaymentInitiationResult,
    PaymentVerificationResult,
    RefundResult,
    WebhookVerificationResult,
)


class PayPakGateway(BasePaymentGateway):
    """PayPak Pakistan Card Scheme Payment Gateway"""

    def __init__(self):
        super().__init__()
        self.gateway_name = "paypak"
        self.flow_type = "api"
        self.currency = "PKR"
        self.supports_refund = True
        self.supports_partial_refund = True

        self.merchant_id = PAYPAK_MERCHANT_ID
        self.api_key = PAYPAK_API_KEY
        self.secret_key = PAYPAK_SECRET_KEY
        self.base_url = PAYPAK_BASE_URL
        self.return_url = PAYPAK_RETURN_URL

    def initialize(self) -> bool:
        """Verify PayPak configuration"""
        return all([
            self.merchant_id,
            self.api_key,
            self.secret_key,
            self.base_url,
        ])

    def generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for PayPak"""
        sorted_data = sorted(data.items())
        param_string = "&".join([f"{k}={v}" for k, v in sorted_data if v])

        signature = hmac.new(
            (self.secret_key or "").encode("utf-8"),
            param_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for PayPak API requests"""
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key or "",
            "X-Merchant-ID": self.merchant_id or "",
        }

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
        """Initiate PayPak payment"""
        try:
            request_data = {
                "merchantId": self.merchant_id,
                "orderId": transaction_id,
                "amount": str(amount),
                "currency": "PKR",
                "customerName": customer_name or "",
                "customerEmail": customer_email or "",
                "customerPhone": customer_phone or "",
                "description": description or f"Order #{order_id}",
                "returnUrl": self.return_url,
                "timestamp": datetime.now().strftime("%Y%m%d%H%M%S"),
            }

            request_data["signature"] = self.generate_signature(request_data)

            url = f"{self.base_url}/api/v1/payment/initiate"

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    url,
                    json=request_data,
                    headers=self._get_headers(),
                )
                response_data = response.json()

            if response_data.get("success"):
                return PaymentInitiationResult(
                    success=True,
                    transaction_id=transaction_id,
                    gateway_transaction_id=response_data.get("transactionId"),
                    redirect_url=response_data.get("paymentUrl"),
                    payment_data=response_data,
                )
            else:
                return PaymentInitiationResult(
                    success=False,
                    transaction_id=transaction_id,
                    error_code=response_data.get("errorCode"),
                    error_message=response_data.get("message"),
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
        """Verify PayPak payment"""
        try:
            url = f"{self.base_url}/api/v1/payment/status"

            request_data = {
                "merchantId": self.merchant_id,
                "orderId": transaction_id,
            }

            if gateway_transaction_id:
                request_data["transactionId"] = gateway_transaction_id

            request_data["signature"] = self.generate_signature(request_data)

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    url,
                    json=request_data,
                    headers=self._get_headers(),
                )
                response_data = response.json()

            status = "pending"
            if response_data.get("status") == "COMPLETED":
                status = "completed"
            elif response_data.get("status") in ["FAILED", "CANCELLED"]:
                status = "failed"

            return PaymentVerificationResult(
                success=status == "completed",
                status=status,
                gateway_transaction_id=response_data.get("transactionId"),
                amount=Decimal(response_data.get("amount", "0")),
                gateway_response=response_data,
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
        """Process PayPak callback"""
        transaction_id = callback_data.get("orderId", "")
        status = callback_data.get("status")

        success = status == "COMPLETED"
        return success, transaction_id, callback_data

    def verify_webhook(
        self, payload: bytes, headers: Dict[str, str]
    ) -> WebhookVerificationResult:
        """Verify PayPak webhook"""
        try:
            data = json.loads(payload.decode("utf-8"))

            received_signature = headers.get("X-Signature", "")
            data_copy = {k: v for k, v in data.items() if k != "signature"}
            expected_signature = self.generate_signature(data_copy)

            if not hmac.compare_digest(received_signature, expected_signature):
                return WebhookVerificationResult(
                    valid=False, error_message="Invalid signature"
                )

            transaction_id = data.get("orderId")
            status = "completed" if data.get("status") == "COMPLETED" else "failed"

            return WebhookVerificationResult(
                valid=True,
                transaction_id=transaction_id,
                status=status,
                parsed_data=data,
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
        """Process PayPak refund"""
        try:
            url = f"{self.base_url}/api/v1/payment/refund"

            request_data = {
                "merchantId": self.merchant_id,
                "orderId": transaction_id,
                "transactionId": gateway_transaction_id,
                "reason": reason or "Customer requested refund",
            }

            if amount:
                request_data["amount"] = str(amount)

            request_data["signature"] = self.generate_signature(request_data)

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    url,
                    json=request_data,
                    headers=self._get_headers(),
                )
                response_data = response.json()

            success = response_data.get("success", False)

            return RefundResult(
                success=success,
                refund_id=response_data.get("refundId"),
                refunded_amount=amount,
                status="completed" if success else "failed",
                error_code=response_data.get("errorCode") if not success else None,
                error_message=response_data.get("message") if not success else None,
            )

        except Exception as e:
            return RefundResult(success=False, error_message=str(e))

    def get_transaction_status(
        self, transaction_id: str, gateway_transaction_id: Optional[str] = None
    ) -> PaymentVerificationResult:
        """Get transaction status"""
        return self.verify_payment(transaction_id, gateway_transaction_id)
