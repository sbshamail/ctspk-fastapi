# src/api/models/productPurchaseModel.py
from typing import TYPE_CHECKING, Literal, Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel
from enum import Enum

if TYPE_CHECKING:
    from src.api.models import Product, User, Shop


class PurchaseType(str, Enum):
    DEBIT = "debit"  # Stock addition
    CREDIT = "credit"  # Stock reduction/return


class TransactionType(str, Enum):
    PURCHASE = "purchase"  # Vendor purchase
    STOCK_ADDITION = "stock_addition"  # Manual stock add
    STOCK_ADJUSTMENT = "stock_adjustment"  # Stock correction
    RETURN = "return"  # Customer return
    DAMAGE = "damage"  # Stock write-off
    TRANSFER = "transfer"  # Inter-shop transfer


class ProductPurchase(TimeStampedModel, table=True):
    __tablename__: Literal["product_purchase"] = "product_purchase"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: Optional[int] = Field(foreign_key="products.id")
    variation_option_id: Optional[int] = Field(foreign_key="variation_options.id", default=None)
    quantity: int
    purchase_date: datetime = Field(default_factory=datetime.utcnow)
    price: Optional[float] = None
    sale_price: Optional[float] = None
    purchase_price: float
    shop_id: int = Field(foreign_key="shops.id")
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    
    # ADDED: Enhanced purchase tracking
    purchase_type: PurchaseType = Field(default=PurchaseType.DEBIT)
    transaction_type: TransactionType = Field(default=TransactionType.PURCHASE)
    reference_number: Optional[str] = Field(max_length=191, unique=True)
    supplier_name: Optional[str] = Field(max_length=191)
    invoice_number: Optional[str] = Field(max_length=191)
    batch_number: Optional[str] = Field(max_length=191)
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    added_by: int = Field(foreign_key="users.id")
    
    # ADDED: Transaction details
    previous_stock: int = Field(default=0)
    new_stock: int = Field(default=0)
    transaction_details: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))

    # relationships
    product: Optional["Product"] = Relationship(back_populates="product_purchases")
    shop: Optional["Shop"] = Relationship()
    added_by_user: Optional["User"] = Relationship()


class ProductPurchaseCreate(SQLModel):
    product_id: Optional[int] = None
    variation_option_id: Optional[int] = None
    quantity: int
    shop_id: int
    purchase_price: float
    purchase_type: PurchaseType = Field(default=PurchaseType.DEBIT)
    transaction_type: TransactionType = Field(default=TransactionType.PURCHASE)
    reference_number: Optional[str] = None
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    sale_price: Optional[float] = None
    price: Optional[float] = None


class ProductPurchaseRead(TimeStampReadModel):
    id: int
    product_id: Optional[int]
    variation_option_id: Optional[int]
    quantity: int
    purchase_price: float
    shop_id: int
    purchase_type: PurchaseType
    transaction_type: TransactionType
    reference_number: Optional[str]
    supplier_name: Optional[str]
    invoice_number: Optional[str]
    batch_number: Optional[str]
    expiry_date: Optional[datetime]
    notes: Optional[str]
    purchase_date: datetime
    previous_stock: int
    new_stock: int
    transaction_details: Optional[Dict[str, Any]]
    added_by: int
    
    # Relationship data
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    variation_title: Optional[str] = None
    added_by_name: Optional[str] = None
    shop_name: Optional[str] = None


class ProductPurchaseVariationOption(TimeStampedModel, table=True):
    __tablename__: Literal["product_purchase_variation_options"] = (
        "product_purchase_variation_options"
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    product_purchase_id: int = Field(foreign_key="product_purchase.id")
    variation_options_id: Optional[int] = Field(foreign_key="variation_options.id")
    price: float
    sale_price: Optional[float] = None
    purchase_price: Optional[float] = None
    language: str = Field(default="en", max_length=191)
    quantity: int
    sku: Optional[str] = Field(max_length=191)
    product_id: Optional[int] = Field(foreign_key="products.id")
    purchase_date: Optional[datetime] = None

    # relationships
    product: Optional["Product"] = Relationship()
    product_purchase: Optional["ProductPurchase"] = Relationship()


class ProductPurchaseVariationOptionCreate(SQLModel):
    product_purchase_id: int
    variation_options_id: Optional[int] = None
    price: float
    quantity: int
    product_id: Optional[int] = None
    purchase_price: Optional[float] = None
    sale_price: Optional[float] = None


class ProductPurchaseVariationOptionRead(TimeStampReadModel):
    id: int
    product_purchase_id: int
    variation_options_id: Optional[int]
    price: float
    quantity: int
    product_id: Optional[int]
    purchase_price: Optional[float]
    sale_price: Optional[float]
    purchase_date: Optional[datetime]