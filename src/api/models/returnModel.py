# src/api/models/returnModel.py
from typing import Optional, List, Dict, Any,TYPE_CHECKING
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_validator
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import  User,  Order,WalletTransaction,ReturnItem,Product,OrderProduct,OrderItem,ReturnRequest

# --------------------------------------------------------------------
# ENUMS
# --------------------------------------------------------------------
class ReturnStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class ReturnType(str, Enum):
    FULL_ORDER = "full_order"
    SINGLE_PRODUCT = "single_product"


class RefundStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


# --------------------------------------------------------------------
# MAIN MODELS
# --------------------------------------------------------------------
class ReturnRequest(TimeStampedModel, table=True):
    __tablename__ = "return_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    return_type: ReturnType = Field(default=ReturnType.SINGLE_PRODUCT, index=True)
    reason: str = Field(nullable=False, max_length=1000)
    status: ReturnStatus = Field(default=ReturnStatus.PENDING, index=True)
    photos: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))

    # Refund details
    refund_amount: float = Field(default=0.0)
    refund_status: RefundStatus = Field(default=RefundStatus.PENDING, index=True)
    wallet_credit_id: Optional[int] = Field(default=None, foreign_key="wallet_transactions.id")

    # Transfer eligibility
    transfer_eligible_at: Optional[datetime] = Field(default=None, index=True)
    transferred_at: Optional[datetime] = Field(default=None)

    # Additional info
    admin_notes: Optional[str] = Field(default=None)
    rejected_reason: Optional[str] = Field(default=None)
    
    # Relationships
    #order: Optional["Order"] = Relationship(back_populates="return_requests")
    #user: Optional["User"] = Relationship(back_populates="return_requests")
    #wallet_transaction: Optional["WalletTransaction"] = Relationship(back_populates="return_request")
    return_items: List["ReturnItem"] = Relationship(back_populates="return_request")


class ReturnItem(TimeStampedModel, table=True):
    __tablename__ = "return_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    return_request_id: int = Field(foreign_key="return_requests.id", index=True)
    order_item_id: int = Field(foreign_key="order_product.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    variation_option_id: Optional[int] = Field(default=None, foreign_key="variation_options.id")
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(default=0.0)
    refund_amount: float = Field(default=0.0)
    
    # Relationships
    return_request: Optional["ReturnRequest"] = Relationship(back_populates="return_items")
    #product: Optional["Product"] = Relationship(back_populates="return_items")
    #order_item: Optional["OrderProduct"] = Relationship(back_populates="return_items")


# --------------------------------------------------------------------
# WALLET MODELS
# --------------------------------------------------------------------
class WalletTransaction(TimeStampedModel, table=True):
    __tablename__ = "wallet_transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    amount: float = Field(default=0.0)
    transaction_type: str = Field(default="credit")  # credit/debit
    balance_after: float = Field(default=0.0)
    description: Optional[str] = Field(default=None)
    is_refund: bool = Field(default=False)
    transfer_eligible_at: Optional[datetime] = Field(default=None, index=True)
    transferred_to_bank: bool = Field(default=False)
    transferred_at: Optional[datetime] = Field(default=None)
    
    # Reference to return request
    return_request_id: Optional[int] = Field(default=None, foreign_key="return_requests.id")
    
    # Relationships
    #user: Optional["User"] = Relationship(back_populates="wallet_transactions")
    #return_request: Optional["ReturnRequest"] = Relationship(back_populates="wallet_transaction")


class UserWallet(TimeStampedModel, table=True):
    __tablename__ = "user_wallets"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, unique=True)
    balance: float = Field(default=0.0)
    total_credited: float = Field(default=0.0)
    total_debited: float = Field(default=0.0)
    
    # Relationships
    #user: Optional["User"] = Relationship(back_populates="wallet")


# --------------------------------------------------------------------
# CRUD SCHEMAS
# --------------------------------------------------------------------
class ReturnItemCreate(SQLModel):
    order_item_id: int
    quantity: int
    reason: Optional[str] = None


class ReturnRequestCreate(SQLModel):
    order_id: int
    return_type: ReturnType
    reason: str
    items: List[ReturnItemCreate]  # For single product returns
    photos: Optional[List[Dict[str, Any]]] = None

    @field_validator('photos', mode='before')
    @classmethod
    def empty_photos_to_none(cls, v):
        """Treat empty array or empty dict as None"""
        if v is None:
            return None
        if isinstance(v, list) and len(v) == 0:
            return None
        return v


class ReturnItemRead(TimeStampReadModel):
    id: int
    return_request_id: int
    order_item_id: int
    product_id: int
    variation_option_id: Optional[int] = None
    quantity: int
    unit_price: float
    refund_amount: float


class ReturnRequestRead(TimeStampReadModel):
    id: int
    order_id: int
    user_id: int
    return_type: ReturnType
    reason: str
    status: ReturnStatus
    refund_amount: float
    refund_status: RefundStatus
    photos: Optional[List[Dict[str, Any]]] = None
    wallet_credit_id: Optional[int] = None
    transfer_eligible_at: Optional[datetime] = None
    transferred_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    rejected_reason: Optional[str] = None
    items: List[ReturnItemRead] = []


class ReturnRequestUpdate(SQLModel):
    status: Optional[ReturnStatus] = None
    admin_notes: Optional[str] = None
    rejected_reason: Optional[str] = None
    photos: Optional[List[Dict[str, Any]]] = None

    @field_validator('photos', mode='before')
    @classmethod
    def empty_photos_to_none(cls, v):
        """Treat empty array or empty dict as None"""
        if v is None:
            return None
        if isinstance(v, list) and len(v) == 0:
            return None
        return v


class WalletTransactionRead(TimeStampReadModel):
    id: int
    user_id: int
    amount: float
    transaction_type: str
    balance_after: float
    description: str
    is_refund: bool
    transfer_eligible_at: Optional[datetime] = None
    transferred_to_bank: bool
    transferred_at: Optional[datetime] = None
    return_request_id: Optional[int] = None


class UserWalletRead(TimeStampReadModel):
    id: int
    user_id: int
    balance: float
    total_credited: float
    total_debited: float


class TransferToBankRequest(SQLModel):
    amount: float
    bank_account_id: int  # Assuming you have bank account model