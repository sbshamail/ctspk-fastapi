# src/api/models/withdrawModel.py
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import Shop, User, OrderProduct,Order

class WithdrawStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"
    FAILED = "failed"

class PaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    DIGITAL_WALLET = "digital_wallet"

class ShopWithdrawRequest(TimeStampedModel, table=True):
    __tablename__ = "shop_withdraw_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    shop_id: int = Field(foreign_key="shops.id", index=True)
    amount: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    admin_commission: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    net_amount: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    status: WithdrawStatus = Field(default=WithdrawStatus.PENDING, index=True)
    payment_method: PaymentMethod = Field(default=PaymentMethod.BANK_TRANSFER)
    
    # Bank details (if bank transfer)
    bank_name: Optional[str] = Field(default=None, max_length=255)
    account_number: Optional[str] = Field(default=None, max_length=50)
    account_holder_name: Optional[str] = Field(default=None, max_length=255)
    ifsc_code: Optional[str] = Field(default=None, max_length=20)
    
    # Cash payment details
    cash_handled_by: Optional[int] = Field(default=None, foreign_key="users.id")
    cash_payment_date: Optional[datetime] = Field(default=None)
    
    # Admin processing
    processed_by: Optional[int] = Field(default=None, foreign_key="users.id")
    processed_at: Optional[datetime] = Field(default=None)
    rejection_reason: Optional[str] = Field(default=None)
    
    # Relationships
    shop: Optional["Shop"] = Relationship(back_populates="withdraw_requests")
    admin_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ShopWithdrawRequest.processed_by]"}
    )
    cash_handler: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ShopWithdrawRequest.cash_handled_by]"}
    )

class ShopEarning(TimeStampedModel, table=True):
    __tablename__ = "shop_earnings"

    id: Optional[int] = Field(default=None, primary_key=True)
    shop_id: int = Field(foreign_key="shops.id", index=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    order_product_id: int = Field(foreign_key="order_product.id", index=True)  # ADDED: Link to specific order product
    order_amount: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    admin_commission: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    shop_earning: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    is_settled: bool = Field(default=False)
    settled_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    shop: Optional["Shop"] = Relationship(back_populates="earnings")
    order: Optional["Order"] = Relationship()
    order_product: Optional["OrderProduct"] = Relationship()  # ADDED: Relationship to order product

# CRUD Schemas
class WithdrawRequestCreate(SQLModel):
    shop_id: int  # Required: Shop ID for withdrawal
    amount: Decimal
    payment_method: PaymentMethod
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_holder_name: Optional[str] = None
    ifsc_code: Optional[str] = None

class WithdrawRequestUpdate(SQLModel):
    status: Optional[WithdrawStatus] = None
    rejection_reason: Optional[str] = None
    processed_by: Optional[int] = None
    cash_handled_by: Optional[int] = None
    cash_payment_date: Optional[datetime] = None

class WithdrawRequestRead(TimeStampReadModel):
    id: int
    shop_id: int
    amount: Decimal
    admin_commission: Decimal
    net_amount: Decimal
    status: WithdrawStatus
    payment_method: PaymentMethod
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_holder_name: Optional[str] = None
    ifsc_code: Optional[str] = None
    cash_handled_by: Optional[int] = None
    cash_payment_date: Optional[datetime] = None
    processed_by: Optional[int] = None
    processed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    shop_name: Optional[str] = None

class ShopEarningRead(TimeStampReadModel):
    id: int
    shop_id: int
    order_id: int
    order_product_id: int  # ADDED
    order_amount: Decimal
    admin_commission: Decimal
    shop_earning: Decimal
    is_settled: bool
    settled_at: Optional[datetime] = None
    order_tracking_number: Optional[str] = None

class ShopBalanceSummary(SQLModel):
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    total_earnings: Decimal
    total_admin_commission: Decimal
    net_balance: Decimal
    pending_withdrawals: Decimal
    available_balance: Decimal
    return_deductions: Decimal = Field(default=Decimal("0.00"))