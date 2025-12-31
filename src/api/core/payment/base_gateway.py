from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class PaymentInitiationResult:
    """Result from payment initiation"""
    success: bool
    transaction_id: str
    gateway_transaction_id: Optional[str] = None
    redirect_url: Optional[str] = None
    payment_data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class PaymentVerificationResult:
    """Result from payment verification"""
    success: bool
    status: str  # pending, completed, failed
    gateway_transaction_id: Optional[str] = None
    amount: Optional[Decimal] = None
    gateway_response: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class RefundResult:
    """Result from refund operation"""
    success: bool
    refund_id: Optional[str] = None
    refunded_amount: Optional[Decimal] = None
    status: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class WebhookVerificationResult:
    """Result from webhook signature verification"""
    valid: bool
    transaction_id: Optional[str] = None
    status: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class BasePaymentGateway(ABC):
    """Abstract base class for all payment gateways"""

    def __init__(self):
        self.gateway_name: str = ""
        self.supports_refund: bool = True
        self.supports_partial_refund: bool = False
        self.flow_type: str = "redirect"
        self.currency: str = "PKR"

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize gateway with configuration. Returns True if successful."""
        pass

    @abstractmethod
    def initiate_payment(
        self,
        transaction_id: str,
        amount: Decimal,
        order_id: int,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentInitiationResult:
        """
        Initiate a payment transaction.

        For redirect-based gateways: Returns redirect URL
        For API-based gateways: Returns payment data/token
        """
        pass

    @abstractmethod
    def verify_payment(
        self,
        transaction_id: str,
        gateway_transaction_id: Optional[str] = None,
        verification_data: Optional[Dict[str, Any]] = None
    ) -> PaymentVerificationResult:
        """Verify payment status with the gateway"""
        pass

    @abstractmethod
    def process_callback(
        self,
        callback_data: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Process callback/redirect data from gateway.
        Returns: (success, transaction_id, parsed_data)
        """
        pass

    @abstractmethod
    def verify_webhook(
        self,
        payload: bytes,
        headers: Dict[str, str]
    ) -> WebhookVerificationResult:
        """Verify webhook signature and parse data"""
        pass

    @abstractmethod
    def refund(
        self,
        transaction_id: str,
        gateway_transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """Process refund (full or partial)"""
        pass

    @abstractmethod
    def get_transaction_status(
        self,
        transaction_id: str,
        gateway_transaction_id: Optional[str] = None
    ) -> PaymentVerificationResult:
        """Get current transaction status from gateway"""
        pass

    def generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate signature for request (override in subclass)"""
        raise NotImplementedError

    def verify_signature(self, data: Dict[str, Any], signature: str) -> bool:
        """Verify signature from gateway (override in subclass)"""
        raise NotImplementedError
