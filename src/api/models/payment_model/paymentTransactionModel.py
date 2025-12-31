from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from sqlalchemy import Column, JSON, Text, Numeric
from sqlmodel import SQLModel, Field, Relationship


if TYPE_CHECKING:
    from src.api.models.order_model.orderModel import Order
    from src.api.models import User


class PaymentGatewayType(str, PyEnum):
    """Supported payment gateways"""
    PAYFAST = "payfast"
    EASYPAISA = "easypaisa"
    JAZZCASH = "jazzcash"
    PAYPAK = "paypak"
    STRIPE = "stripe"
    CASH_ON_DELIVERY = "cod"


class PaymentTransactionStatus(str, PyEnum):
    """Payment transaction status"""
    INITIATED = "initiated"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    EXPIRED = "expired"


class PaymentFlowType(str, PyEnum):
    """Payment flow type"""
    REDIRECT = "redirect"
    API = "api"
    MOBILE_WALLET = "mobile_wallet"


class PaymentTransaction(SQLModel, table=True):
    """Payment transaction model for tracking all payment attempts"""
    __tablename__ = "payment_transactions"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Transaction Identifiers
    transaction_id: str = Field(max_length=191, unique=True, index=True)
    gateway_transaction_id: Optional[str] = Field(default=None, max_length=191, index=True)
    gateway_reference: Optional[str] = Field(default=None, max_length=191)

    # Order Reference
    order_id: int = Field(foreign_key="orders.id", index=True)

    # Gateway Information
    gateway_type: str = Field(max_length=50, index=True)
    flow_type: str = Field(default="redirect", max_length=50)

    # Amount Information
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    currency: str = Field(default="PKR", max_length=3)
    fee: Optional[Decimal] = Field(default=Decimal("0.00"), sa_column=Column(Numeric(10, 2)))
    net_amount: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(12, 2)))

    # Refund Tracking
    refunded_amount: Decimal = Field(default=Decimal("0.00"), sa_column=Column(Numeric(12, 2), nullable=False))

    # Status
    status: str = Field(default="initiated", max_length=50, index=True)

    # Customer Information
    customer_id: Optional[int] = Field(default=None, foreign_key="users.id")
    customer_name: Optional[str] = Field(default=None, max_length=191)
    customer_email: Optional[str] = Field(default=None, max_length=191)
    customer_phone: Optional[str] = Field(default=None, max_length=50)

    # Gateway-Specific Data (stored as JSON)
    gateway_request: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    gateway_response: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Redirect URLs
    redirect_url: Optional[str] = Field(default=None, max_length=500)
    callback_url: Optional[str] = Field(default=None, max_length=500)

    # Webhook Data
    webhook_received: bool = Field(default=False)
    webhook_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    webhook_received_at: Optional[datetime] = Field(default=None)

    # Error Handling
    error_code: Optional[str] = Field(default=None, max_length=50)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Metadata
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, sa_column=Column(Text))
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)

    # Relationships
    order: Optional["Order"] = Relationship(back_populates="payment_transactions")
    customer: Optional["User"] = Relationship()


class PaymentTransactionCreate(SQLModel):
    """Schema for creating a payment transaction"""
    order_id: int
    gateway_type: str
    amount: Decimal
    currency: str = "PKR"
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class PaymentTransactionRead(SQLModel):
    """Schema for reading a payment transaction"""
    id: int
    transaction_id: str
    gateway_transaction_id: Optional[str]
    order_id: int
    gateway_type: str
    flow_type: str
    amount: Decimal
    currency: str
    fee: Optional[Decimal]
    net_amount: Optional[Decimal]
    refunded_amount: Decimal
    status: str
    customer_name: Optional[str]
    customer_email: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class RefundRequest(SQLModel):
    """Schema for refund request"""
    transaction_id: str
    amount: Optional[Decimal] = None  # None means full refund
    reason: Optional[str] = None
