# src/api/models/transactionLogModel.py
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, Enum
from enum import Enum as PyEnum
from decimal import Decimal

if TYPE_CHECKING:
    from src.api.models import Product, Order, OrderProduct, User, Shop, VariationOption

class TransactionType(PyEnum):
    """Types of transactions"""
    PRODUCT_CREATE = "product_create"
    PRODUCT_UPDATE = "product_update"
    PRODUCT_DELETE = "product_delete"
    PRICE_CHANGE = "price_change"
    STOCK_ADDITION = "stock_addition"
    STOCK_DEDUCTION = "stock_deduction"
    STOCK_ADJUSTMENT = "stock_adjustment"
    ORDER_PLACED = "order_placed"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_RETURNED = "order_returned"
    ORDER_REFUNDED = "order_refunded"
    ORDER_STATUS_CHANGE = "order_status_change"
    VARIATION_CREATE = "variation_create"
    VARIATION_UPDATE = "variation_update"
    VARIATION_DELETE = "variation_delete"
    IMPORT_BATCH = "import_batch"
    EXPORT_BATCH = "export_batch"

class TransactionDirection(PyEnum):
    """Direction of quantity change"""
    INCREASE = "increase"
    DECREASE = "decrease"
    NO_CHANGE = "no_change"

class TransactionLog(SQLModel, table=True):
    """Master table for all transaction logs"""
    __tablename__: str = "transaction_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_type: str = Field(index=True)  # Using string for flexibility
    transaction_date: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Reference fields
    product_id: Optional[int] = Field(foreign_key="products.id", index=True, default=None)
    variation_option_id: Optional[int] = Field(foreign_key="variation_options.id", default=None)
    order_id: Optional[int] = Field(foreign_key="orders.id", default=None)
    order_product_id: Optional[int] = Field(foreign_key="order_product.id", default=None)
    shop_id: Optional[int] = Field(foreign_key="shops.id", default=None)
    user_id: Optional[int] = Field(foreign_key="users.id", default=None)
    
    # Transaction details
    quantity_change: Optional[int] = None  # Positive for increase, negative for decrease
    direction: TransactionDirection = Field(default=TransactionDirection.NO_CHANGE)
    purchase_price: Optional[float] = None  # Only for stock additions
    unit_price: Optional[float] = None  # Product price at transaction time
    sale_price: Optional[float] = None  # Sale price at transaction time
    previous_price: Optional[float] = None  # Price before change
    new_price: Optional[float] = None  # Price after change
    previous_quantity: Optional[int] = None  # Quantity before change
    new_quantity: Optional[int] = None  # Quantity after change
    
    # Financial details
    subtotal: Optional[float] = None  # For order transactions
    discount: Optional[float] = None  # For order transactions
    tax: Optional[float] = None  # For order transactions
    total: Optional[float] = None  # For order transactions
    
    # Metadata
    reference_number: Optional[str] = Field(max_length=191, index=True)
    invoice_number: Optional[str] = Field(max_length=191, default=None)
    batch_number: Optional[str] = Field(max_length=191, default=None)
    notes: Optional[str] = None  # Custom notes
    auto_generated_notes: Optional[str] = None  # System-generated notes
    transaction_details: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON), default=None)
    
    # Flags
    is_duplicate: bool = Field(default=False)
    is_system_generated: bool = Field(default=False)
    requires_review: bool = Field(default=False)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Relationships
    product: Optional["Product"] = Relationship(back_populates="transaction_logs")
    variation_option: Optional["VariationOption"] = Relationship()
    order: Optional["Order"] = Relationship()
    order_product: Optional["OrderProduct"] = Relationship()
    shop: Optional["Shop"] = Relationship()
    user: Optional["User"] = Relationship()

class TransactionLogCreate(SQLModel):
    """Schema for creating transaction logs"""
    transaction_type: str
    product_id: Optional[int] = None
    variation_option_id: Optional[int] = None
    order_id: Optional[int] = None
    order_product_id: Optional[int] = None
    shop_id: Optional[int] = None
    user_id: Optional[int] = None
    quantity_change: Optional[int] = None
    purchase_price: Optional[float] = None
    unit_price: Optional[float] = None
    sale_price: Optional[float] = None
    previous_price: Optional[float] = None
    new_price: Optional[float] = None
    previous_quantity: Optional[int] = None
    new_quantity: Optional[int] = None
    subtotal: Optional[float] = None
    discount: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    reference_number: Optional[str] = None
    invoice_number: Optional[str] = None
    batch_number: Optional[str] = None
    notes: Optional[str] = None
    transaction_details: Optional[Dict[str, Any]] = None

class TransactionLogRead(SQLModel):
    """Schema for reading transaction logs"""
    id: int
    transaction_type: str
    transaction_date: datetime
    product_id: Optional[int] = None
    variation_option_id: Optional[int] = None
    order_id: Optional[int] = None
    order_product_id: Optional[int] = None
    shop_id: Optional[int] = None
    user_id: Optional[int] = None
    quantity_change: Optional[int] = None
    direction: TransactionDirection
    purchase_price: Optional[float] = None
    unit_price: Optional[float] = None
    sale_price: Optional[float] = None
    previous_price: Optional[float] = None
    new_price: Optional[float] = None
    previous_quantity: Optional[int] = None
    new_quantity: Optional[int] = None
    subtotal: Optional[float] = None
    discount: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    reference_number: Optional[str] = None
    invoice_number: Optional[str] = None
    batch_number: Optional[str] = None
    notes: Optional[str] = None
    auto_generated_notes: Optional[str] = None
    is_duplicate: bool
    is_system_generated: bool
    requires_review: bool
    created_at: datetime
    
    # Relationship data
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    variation_title: Optional[str] = None
    order_tracking_number: Optional[str] = None
    user_name: Optional[str] = None
    shop_name: Optional[str] = None