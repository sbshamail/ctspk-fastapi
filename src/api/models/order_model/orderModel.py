# src/api/models/orderModel.py
from typing import TYPE_CHECKING, Literal, Optional, List, Dict, Any
from sqlalchemy import Column, JSON, Text, Enum
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel
from enum import Enum as PyEnum

if TYPE_CHECKING:
    from src.api.models import User, Shop, Product, VariationOption, Category


class OrderStatusEnum(str, PyEnum):
    PENDING = "order-pending"
    PROCESSING = "order-processing"
    COMPLETED = "order-completed"
    REFUNDED = "order-refunded"
    FAILED = "order-failed"
    CANCELLED = "order-cancelled"
    AT_LOCAL_FACILITY = "order-at-local-facility"
    OUT_FOR_DELIVERY = "order-out-for-delivery"
    AT_DISTRIBUTION_CENTER = "order-at-distribution-center"
    PACKED = "order-packed"


class PaymentStatusEnum(str, PyEnum):
    PENDING = "payment-pending"
    PROCESSING = "payment-processing"
    SUCCESS = "payment-success"
    FAILED = "payment-failed"
    REVERSAL = "payment-reversal"
    CASH_ON_DELIVERY = "payment-cash-on-delivery"
    CASH = "payment-cash"
    WALLET = "payment-wallet"
    AWAITING_APPROVAL = "payment-awaiting-for-approval"


class Order(TimeStampedModel, table=True):
    __tablename__: Literal["orders"] = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    tracking_number: str = Field(max_length=191, unique=True)
    customer_id: Optional[int] = Field(default=None, foreign_key="users.id")
    customer_contact: str = Field(max_length=191)
    customer_name: Optional[str] = Field(max_length=191, default=None)
    amount: float = Field()
    sales_tax: Optional[float] = Field(default=None)
    paid_total: Optional[float] = Field(default=None)
    total: Optional[float] = Field(default=None)
    cancelled_amount: Decimal = Field(
        default=Decimal("0.00"), max_digits=10, decimal_places=2
    )
    admin_commission_amount: Decimal = Field(
        default=Decimal("0.00"), max_digits=10, decimal_places=2
    )
    language: str = Field(default="en", max_length=191)
    coupon_id: Optional[int] = Field(default=None, foreign_key="coupons.id")
    shop_id: Optional[int] = Field(default=None, foreign_key="shops.id")
    discount: Optional[float] = Field(default=None)
    payment_gateway: Optional[str] = Field(default=None, max_length=191)
    shipping_address: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    billing_address: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    logistics_provider: Optional[int] = Field(default=None)
    delivery_fee: Optional[float] = Field(default=None)
    delivery_time: Optional[str] = Field(default=None, max_length=191)
    order_status: OrderStatusEnum = Field(default=OrderStatusEnum.PENDING)
    payment_status: PaymentStatusEnum = Field(default=PaymentStatusEnum.PENDING)
    # order_status: OrderStatusEnum = Field(default=OrderStatusEnum.PENDING, sa_column=Column(Enum(OrderStatusEnum)))
    # payment_status: PaymentStatusEnum = Field(default=PaymentStatusEnum.PENDING, sa_column=Column(Enum(PaymentStatusEnum)))
    fullfillment_id: Optional[int] = Field(
        default=None, foreign_key="users.id"
    )  # Foreign key to users
    assign_date: Optional[datetime] = Field(default=None)

    # relationships
    customer: Optional["User"] = Relationship(
        back_populates="customer_orders",
        sa_relationship_kwargs={"foreign_keys": "[Order.customer_id]"},
    )

    fullfillment_user: Optional["User"] = Relationship(
        back_populates="fullfillment_orders",
        sa_relationship_kwargs={"foreign_keys": "[Order.fullfillment_id]"},
    )

    shop: Optional["Shop"] = Relationship(
        back_populates="orders",
        sa_relationship_kwargs={"foreign_keys": "[Order.shop_id]"},
    )

    order_products: List["OrderProduct"] = Relationship(back_populates="orders")
    # order_status_history: Optional["OrderStatus"] = Relationship(back_populates="order")
    order_status_history: Optional["OrderStatus"] = Relationship(
        back_populates="orders",
        sa_relationship_kwargs={
            "foreign_keys": "[OrderStatus.order_id]",
            "uselist": False,  # One-to-one relationship
        },
    )


class OrderProduct(TimeStampedModel, table=True):
    __tablename__: Literal["order_product"] = "order_product"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    product_id: int = Field(foreign_key="products.id")
    variation_option_id: Optional[int] = Field(
        default=None, foreign_key="variation_options.id"
    )
    order_quantity: str = Field(max_length=191)
    unit_price: float = Field()
    subtotal: float = Field()
    admin_commission: Decimal = Field(
        default=Decimal("0.00"), max_digits=10, decimal_places=2
    )
    deleted_at: Optional[datetime] = None

    # relationships
    orders: "Order" = Relationship(back_populates="order_products")
    product: "Product" = Relationship(back_populates="order_products")
    # variation_option: Optional["VariationOption"] = Relationship()


class OrderStatus(TimeStampedModel, table=True):
    __tablename__ = "orders_status"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", unique=True)  # Add foreign key here
    language: str = Field(default="en", max_length=191)
    order_pending_date: Optional[datetime] = Field(default=None)
    order_processing_date: Optional[datetime] = Field(default=None)
    order_completed_date: Optional[datetime] = Field(default=None)
    order_refunded_date: Optional[datetime] = Field(default=None)
    order_failed_date: Optional[datetime] = Field(default=None)
    order_cancelled_date: Optional[datetime] = Field(default=None)
    order_at_local_facility_date: Optional[datetime] = Field(default=None)
    order_out_for_delivery_date: Optional[datetime] = Field(default=None)
    order_packed_date: Optional[datetime] = Field(default=None)
    order_at_distribution_center_date: Optional[datetime] = Field(default=None)

    # relationships - specify the foreign key explicitly
    orders: Optional["Order"] = Relationship(
        back_populates="order_status_history",
        sa_relationship_kwargs={"foreign_keys": "[OrderStatus.order_id]"},
    )
    # relationships


# order: "Order" = Relationship(back_populates="order_status_history")


# Create Schemas
class OrderProductCreate(SQLModel):
    product_id: int
    variation_option_id: Optional[int] = None
    order_quantity: str
    unit_price: float
    subtotal: float
    # admin_commission will be calculated automatically


class OrderCreate(SQLModel):
    customer_id: Optional[int] = None
    customer_contact: str
    customer_name: Optional[str] = None
    amount: float
    sales_tax: Optional[float] = None
    paid_total: Optional[float] = None
    total: Optional[float] = None
    shop_id: Optional[int] = None
    discount: Optional[float] = None
    payment_gateway: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    logistics_provider: Optional[int] = None
    delivery_fee: Optional[float] = None
    delivery_time: Optional[str] = None
    order_products: List[OrderProductCreate]


class OrderUpdate(SQLModel):
    customer_id: Optional[int] = None
    customer_contact: Optional[str] = None
    customer_name: Optional[str] = None
    amount: Optional[float] = None
    sales_tax: Optional[float] = None
    paid_total: Optional[float] = None
    total: Optional[float] = None
    shop_id: Optional[int] = None
    discount: Optional[float] = None
    payment_gateway: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    logistics_provider: Optional[int] = None
    delivery_fee: Optional[float] = None
    delivery_time: Optional[str] = None
    order_status: Optional[OrderStatusEnum] = None
    payment_status: Optional[PaymentStatusEnum] = None
    fullfillment_id: Optional[int] = None
    assign_date: Optional[datetime] = None


class OrderStatusUpdate(SQLModel):
    order_status: Optional[OrderStatusEnum] = None
    payment_status: Optional[PaymentStatusEnum] = None


class OrderRead(TimeStampReadModel):
    id: int
    tracking_number: str
    customer_id: Optional[int] = None
    customer_contact: str
    customer_name: Optional[str] = None
    amount: float
    sales_tax: Optional[float] = None
    paid_total: Optional[float] = None
    total: Optional[float] = None
    cancelled_amount: Decimal
    admin_commission_amount: Decimal
    language: str
    coupon_id: Optional[int] = None
    shop_id: Optional[int] = None
    discount: Optional[float] = None
    payment_gateway: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    logistics_provider: Optional[int] = None
    delivery_fee: Optional[float] = None
    delivery_time: Optional[str] = None
    order_status: OrderStatusEnum
    payment_status: PaymentStatusEnum
    fullfillment_id: Optional[int] = None
    assign_date: Optional[datetime] = None


class OrderProductRead(TimeStampReadModel):
    id: int
    order_id: int
    product_id: int
    variation_option_id: Optional[int] = None
    order_quantity: str
    unit_price: float
    subtotal: float
    admin_commission: Decimal


class OrderReadNested(OrderRead):
    order_products: List[OrderProductRead] = []
    order_status_history: Optional["OrderStatusRead"] = None


class OrderStatusRead(TimeStampReadModel):
    id: int
    order_id: int
    language: str
    order_pending_date: Optional[datetime] = None
    order_processing_date: Optional[datetime] = None
    order_completed_date: Optional[datetime] = None
    order_refunded_date: Optional[datetime] = None
    order_failed_date: Optional[datetime] = None
    order_cancelled_date: Optional[datetime] = None
    order_at_local_facility_date: Optional[datetime] = None
    order_out_for_delivery_date: Optional[datetime] = None
    order_packed_date: Optional[datetime] = None
    order_at_distribution_center_date: Optional[datetime] = None
