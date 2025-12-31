import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
import httpx

from src.config import (
    EASYPAISA_STORE_ID,
    EASYPAISA_HASH_KEY,
    EASYPAISA_BASE_URL,
    EASYPAISA_RETURN_URL,
)
from ..base_gateway import (
    BasePaymentGateway,
    PaymentInitiationResult,
    PaymentVerificationResult,
    RefundResult,
    WebhookVerificationResult,
)


class EasyPaisaGateway(BasePaymentGateway):
    """EasyPaisa Mobile Wallet Payment Gateway"""

    def __init__(self):
        super().__init__()
        self.gateway_name = "easypaisa"
        self.flow_type = "redirect"
        self.currency = "PKR"
        self.supports_refund = True
        self.supports_partial_refund = True

        self.store_id = EASYPAISA_STORE_ID
        self.hash_key = EASYPAISA_HASH_KEY
        self.base_url = EASYPAISA_BASE_URL
        self.return_url = EASYPAISA_RETURN_URL

    def initialize(self) -> bool:
        """Verify EasyPaisa configuration"""
        return all([self.store_id, self.hash_key, self.base_url])

    def generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate SHA256 hash for EasyPaisa"""
        hash_string = (
            f"{data.get('amount', '')}{data.get('orderRefNum', '')}"
            f"{data.get('merchantHashedReq', '')}{self.hash_key}"
        )
        return hashlib.sha256(hash_string.encode()).hexdigest()

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
        """Initiate EasyPaisa payment"""
        try:
            expiry_date = (datetime.now() + timedelta(hours=1)).strftime(
                "%Y%m%d %H%M%S"
            )

            request_data = {
                "storeId": self.store_id,
                "amount": str(amount),
                "orderRefNum": transaction_id,
                "expiryDate": expiry_date,
                "autoRedirect": "1",
                "paymentMethod": "MA_PAYMENT_METHOD",
                "mobileNum": customer_phone or "",
                "emailAddr": customer_email or "",
                "postBackURL": self.return_url,
            }

            request_data["merchantHashedReq"] = self.generate_signature(request_data)

            redirect_url = f"{self.base_url}/easypay/Index.jsf"

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
        """Verify EasyPaisa payment"""
        try:
            url = f"{self.base_url}/easypay/Confirm.jsf"

            request_data = {
                "storeId": self.store_id,
                "orderRefNumber": transaction_id,
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, data=request_data)
                response_data = response.json()

            status = "pending"
            if response_data.get("responseCode") == "0000":
                status = "completed"
            elif response_data.get("responseCode") != "0001":
                status = "failed"

            return PaymentVerificationResult(
                success=status == "completed",
                status=status,
                gateway_transaction_id=response_data.get("transactionId"),
                amount=Decimal(response_data.get("paidAmount", "0")),
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
        """Process EasyPaisa callback"""
        transaction_id = callback_data.get("orderRefNumber", "")
        response_code = callback_data.get("responseCode")

        success = response_code == "0000"
        return success, transaction_id, callback_data

    def verify_webhook(
        self, payload: bytes, headers: Dict[str, str]
    ) -> WebhookVerificationResult:
        """Verify EasyPaisa webhook"""
        try:
            data = json.loads(payload.decode("utf-8"))

            transaction_id = data.get("orderRefNumber")
            status = "completed" if data.get("responseCode") == "0000" else "failed"

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
        """Process EasyPaisa refund"""
        try:
            url = f"{self.base_url}/easypay/Refund.jsf"

            request_data = {
                "storeId": self.store_id,
                "orderRefNumber": transaction_id,
                "transactionId": gateway_transaction_id,
                "reason": reason or "Customer requested refund",
            }

            if amount:
                request_data["refundAmount"] = str(amount)

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, data=request_data)
                response_data = response.json()

            success = response_data.get("responseCode") == "0000"

            return RefundResult(
                success=success,
                refund_id=response_data.get("refundId"),
                refunded_amount=amount,
                status="completed" if success else "failed",
                error_code=response_data.get("responseCode") if not success else None,
                error_message=response_data.get("responseDesc") if not success else None,
            )

        except Exception as e:
            return RefundResult(success=False, error_message=str(e))

    def get_transaction_status(
        self, transaction_id: str, gateway_transaction_id: Optional[str] = None
    ) -> PaymentVerificationResult:
        """Get transaction status"""
        return self.verify_payment(transaction_id, gateway_transaction_id)
