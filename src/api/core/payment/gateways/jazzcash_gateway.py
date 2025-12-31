import hashlib
import hmac
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
import httpx

from src.config import (
    JAZZCASH_MERCHANT_ID,
    JAZZCASH_PASSWORD,
    JAZZCASH_INTEGRITY_SALT,
    JAZZCASH_BASE_URL,
    JAZZCASH_RETURN_URL,
)
from ..base_gateway import (
    BasePaymentGateway,
    PaymentInitiationResult,
    PaymentVerificationResult,
    RefundResult,
    WebhookVerificationResult,
)


class JazzCashGateway(BasePaymentGateway):
    """JazzCash Mobile Wallet Payment Gateway"""

    def __init__(self):
        super().__init__()
        self.gateway_name = "jazzcash"
        self.flow_type = "redirect"
        self.currency = "PKR"
        self.supports_refund = True
        self.supports_partial_refund = False

        self.merchant_id = JAZZCASH_MERCHANT_ID
        self.password = JAZZCASH_PASSWORD
        self.integrity_salt = JAZZCASH_INTEGRITY_SALT
        self.base_url = JAZZCASH_BASE_URL
        self.return_url = JAZZCASH_RETURN_URL

    def initialize(self) -> bool:
        """Verify JazzCash configuration"""
        return all([
            self.merchant_id,
            self.password,
            self.integrity_salt,
            self.base_url,
        ])

    def generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate JazzCash secure hash"""
        sorted_keys = sorted(data.keys())
        hash_string = self.integrity_salt or ""

        for key in sorted_keys:
            if data[key]:
                hash_string += f"&{data[key]}"

        return hmac.new(
            (self.integrity_salt or "").encode(),
            hash_string.encode(),
            hashlib.sha256,
        ).hexdigest()

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
        """Initiate JazzCash payment"""
        try:
            now = datetime.now()
            expiry_date = (now + timedelta(hours=1)).strftime("%Y%m%d%H%M%S")

            request_data = {
                "pp_Version": "1.1",
                "pp_TxnType": "MWALLET",
                "pp_Language": "EN",
                "pp_MerchantID": self.merchant_id,
                "pp_SubMerchantID": "",
                "pp_Password": self.password,
                "pp_BankID": "TBANK",
                "pp_ProductID": "RETL",
                "pp_TxnRefNo": transaction_id,
                "pp_Amount": str(int(amount * 100)),
                "pp_TxnCurrency": "PKR",
                "pp_TxnDateTime": now.strftime("%Y%m%d%H%M%S"),
                "pp_BillReference": f"order{order_id}",
                "pp_Description": description or f"Order #{order_id}",
                "pp_TxnExpiryDateTime": expiry_date,
                "pp_ReturnURL": self.return_url,
                "ppmpf_1": customer_phone or "",
                "ppmpf_2": customer_email or "",
                "ppmpf_3": customer_name or "",
                "ppmpf_4": "",
                "ppmpf_5": "",
            }

            request_data["pp_SecureHash"] = self.generate_signature(request_data)

            redirect_url = (
                f"{self.base_url}/CustomerPortal/transactionmanagement/merchantform/"
            )

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
        """Verify JazzCash payment"""
        try:
            url = f"{self.base_url}/ApplicationAPI/API/PaymentInquiry/Inquire"

            request_data = {
                "pp_MerchantID": self.merchant_id,
                "pp_Password": self.password,
                "pp_TxnRefNo": transaction_id,
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=request_data)
                response_data = response.json()

            status = "pending"
            if response_data.get("pp_ResponseCode") == "000":
                status = "completed"
            elif response_data.get("pp_ResponseCode") not in ["124", "125"]:
                status = "failed"

            return PaymentVerificationResult(
                success=status == "completed",
                status=status,
                gateway_transaction_id=response_data.get("pp_TxnRefNo"),
                amount=Decimal(response_data.get("pp_Amount", "0")) / 100,
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
        """Process JazzCash callback"""
        transaction_id = callback_data.get("pp_TxnRefNo", "")
        response_code = callback_data.get("pp_ResponseCode")

        success = response_code == "000"
        return success, transaction_id, callback_data

    def verify_webhook(
        self, payload: bytes, headers: Dict[str, str]
    ) -> WebhookVerificationResult:
        """Verify JazzCash webhook"""
        try:
            data = json.loads(payload.decode("utf-8"))

            received_hash = data.pop("pp_SecureHash", "")
            expected_hash = self.generate_signature(data)

            if not hmac.compare_digest(received_hash, expected_hash):
                return WebhookVerificationResult(
                    valid=False, error_message="Invalid secure hash"
                )

            transaction_id = data.get("pp_TxnRefNo")
            status = "completed" if data.get("pp_ResponseCode") == "000" else "failed"

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
        """Process JazzCash refund"""
        try:
            url = f"{self.base_url}/ApplicationAPI/API/Refund/DoRefund"

            request_data = {
                "pp_MerchantID": self.merchant_id,
                "pp_Password": self.password,
                "pp_TxnRefNo": transaction_id,
                "pp_RefundReason": reason or "Customer requested refund",
            }

            if amount:
                request_data["pp_RefundAmount"] = str(int(amount * 100))

            request_data["pp_SecureHash"] = self.generate_signature(request_data)

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=request_data)
                response_data = response.json()

            success = response_data.get("pp_ResponseCode") == "000"

            return RefundResult(
                success=success,
                refund_id=response_data.get("pp_RefundTxnRefNo"),
                refunded_amount=amount,
                status="completed" if success else "failed",
                error_code=response_data.get("pp_ResponseCode") if not success else None,
                error_message=response_data.get("pp_ResponseMessage")
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
