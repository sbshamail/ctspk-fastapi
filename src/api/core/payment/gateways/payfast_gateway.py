import hashlib
import hmac
import json
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
import httpx

from src.config import (
    PAYFAST_MERCHANT_ID,
    PAYFAST_SECURED_KEY,
    PAYFAST_BASE_URL,
    PAYFAST_RETURN_URL,
    PAYFAST_CANCEL_URL,
)
from ..base_gateway import (
    BasePaymentGateway,
    PaymentInitiationResult,
    PaymentVerificationResult,
    RefundResult,
    WebhookVerificationResult,
)


class PayFastGateway(BasePaymentGateway):
    """PayFast Pakistan Payment Gateway Implementation"""

    def __init__(self):
        super().__init__()
        self.gateway_name = "payfast"
        self.flow_type = "redirect"
        self.currency = "PKR"
        self.supports_refund = True
        self.supports_partial_refund = False

        self.merchant_id = PAYFAST_MERCHANT_ID
        self.secured_key = PAYFAST_SECURED_KEY
        self.base_url = PAYFAST_BASE_URL
        self.return_url = PAYFAST_RETURN_URL
        self.cancel_url = PAYFAST_CANCEL_URL

    def initialize(self) -> bool:
        """Verify PayFast configuration"""
        return all([
            self.merchant_id,
            self.secured_key,
            self.base_url,
            self.return_url,
        ])

    def generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for PayFast"""
        sorted_data = sorted(data.items())
        param_string = "&".join([f"{k}={v}" for k, v in sorted_data if v])

        signature = hmac.new(
            self.secured_key.encode("utf-8"),
            param_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature

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
        """Initiate PayFast payment (redirect-based)"""
        try:
            request_data = {
                "MERCHANT_ID": self.merchant_id,
                "MERCHANT_NAME": "CTSPK Store",
                "TOKEN": transaction_id,
                "PROCCODE": "00",
                "TXNAMT": str(int(amount * 100)),
                "CUSTOMER_MOBILE_NO": customer_phone or "",
                "CUSTOMER_EMAIL_ADDRESS": customer_email or "",
                "VERSION": "MERCHANT-CART-0.1",
                "TXNDESC": description or f"Order #{order_id}",
                "SUCCESS_URL": self.return_url,
                "FAILURE_URL": self.cancel_url,
                "BASKET_ID": str(order_id),
                "ORDER_DATE": datetime.now().strftime("%Y%m%d%H%M%S"),
                "CHECKOUT_URL": f"{self.return_url}?token={transaction_id}",
            }

            request_data["SIGNATURE"] = self.generate_signature(request_data)

            redirect_url = f"{self.base_url}/Ecommerce/api/Transaction/PostTransaction"

            return PaymentInitiationResult(
                success=True,
                transaction_id=transaction_id,
                redirect_url=redirect_url,
                payment_data=request_data,
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
        """Verify PayFast payment status"""
        try:
            url = f"{self.base_url}/Ecommerce/api/Transaction/GetTransactionStatus"

            request_data = {
                "MERCHANT_ID": self.merchant_id,
                "TOKEN": transaction_id,
            }
            request_data["SIGNATURE"] = self.generate_signature(request_data)

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=request_data)
                response_data = response.json()

            status = "pending"
            if response_data.get("RESPONSE_CODE") == "00":
                status = "completed"
            elif response_data.get("RESPONSE_CODE") in ["01", "02", "03"]:
                status = "failed"

            return PaymentVerificationResult(
                success=status == "completed",
                status=status,
                gateway_transaction_id=response_data.get("TRANSACTION_ID"),
                amount=Decimal(response_data.get("TXNAMT", "0")) / 100,
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
        """Process PayFast callback/redirect"""
        transaction_id = callback_data.get("TOKEN") or callback_data.get("token", "")
        response_code = callback_data.get("RESPONSE_CODE") or callback_data.get(
            "response_code"
        )

        success = response_code == "00"
        return success, transaction_id, callback_data

    def verify_webhook(
        self, payload: bytes, headers: Dict[str, str]
    ) -> WebhookVerificationResult:
        """Verify PayFast webhook (IPN)"""
        try:
            data = json.loads(payload.decode("utf-8"))

            received_signature = data.pop("SIGNATURE", "")
            expected_signature = self.generate_signature(data)

            if not hmac.compare_digest(received_signature, expected_signature):
                return WebhookVerificationResult(
                    valid=False, error_message="Invalid signature"
                )

            transaction_id = data.get("TOKEN")
            status = "completed" if data.get("RESPONSE_CODE") == "00" else "failed"

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
        """Process PayFast refund"""
        try:
            url = f"{self.base_url}/Ecommerce/api/Transaction/RefundTransaction"

            request_data = {
                "MERCHANT_ID": self.merchant_id,
                "TOKEN": transaction_id,
                "TRANSACTION_ID": gateway_transaction_id,
                "REFUND_REASON": reason or "Customer requested refund",
            }

            if amount:
                request_data["REFUND_AMOUNT"] = str(int(amount * 100))

            request_data["SIGNATURE"] = self.generate_signature(request_data)

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=request_data)
                response_data = response.json()

            success = response_data.get("RESPONSE_CODE") == "00"

            return RefundResult(
                success=success,
                refund_id=response_data.get("REFUND_ID"),
                refunded_amount=amount,
                status="completed" if success else "failed",
                error_code=response_data.get("RESPONSE_CODE") if not success else None,
                error_message=response_data.get("RESPONSE_MESSAGE")
                if not success
                else None,
            )

        except Exception as e:
            return RefundResult(success=False, error_message=str(e))

    def get_transaction_status(
        self, transaction_id: str, gateway_transaction_id: Optional[str] = None
    ) -> PaymentVerificationResult:
        """Get transaction status"""
        return self.verify_payment(transaction_id, gateway_transaction_id)
