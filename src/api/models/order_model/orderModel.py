# src/api/models/orderModel.py
from typing import TYPE_CHECKING, Literal, Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


class OrderStatus(str, Enum):
    ORDER_PENDING = "order-pending"
    ORDER_PROCESSING = "order-processing"
    ORDER_COMPLETED = "order-completed"
    ORDER_REFUNDED = "order-refunded"
    ORDER_FAILED = "order-failed"
    ORDER_CANCELLED = "order-cancelled"
    ORDER_AT_LOCAL_FACILITY = "order-at-local-facility"
    ORDER_OUT_FOR_DELIVERY = "order-out-for-delivery"
    ORDER_AT_DISTRIBUTION_CENTER = "order-at-distribution-center"
    ORDER_PACKED = "order-packed"


class PaymentStatus(str, Enum):
    PAYMENT_PENDING = "payment-pending"
    PAYMENT_PROCESSING = "payment-processing"
    PAYMENT_SUCCESS = "payment-success"
    PAYMENT_FAILED = "payment-failed"
    PAYMENT_REVERSAL = "payment-reversal"
    PAYMENT_CASH_ON_DELIVERY = "payment-cash-on-delivery"
    PAYMENT_CASH = "payment-cash"
    PAYMENT_WALLET = "payment-wallet"
    PAYMENT_AWAITING_APPROVAL = "payment-awaiting-for-approval"


if TYPE_CHECKING:
    from src.api.models import User, Shop, OrderProduct


class Order(TimeStampedModel, table=True):
    __tablename__: Literal["orders"] = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    tracking_number: str = Field(max_length=191, unique=True)
    customer_id: Optional[int] = Field(foreign_key="users.id")
    customer_contact: str = Field(max_length=191)
    customer_name: Optional[str] = Field(max_length=191)
    amount: float
    sales_tax: Optional[float] = None
    paid_total: Optional[float] = None
    total: Optional[float] = None
    cancelled_amount: float = Field(default=0.00)
    admin_commission_amount: float = Field(default=0.00)
    language: str = Field(default="en", max_length=191)
    coupon_id: Optional[int] = Field(foreign_key="coupons.id")
    parent_id: Optional[int] = Field(foreign_key="orders.id")
    shop_id: Optional[int] = Field(foreign_key="shops.id")
    discount: Optional[float] = None
    payment_gateway: Optional[str] = Field(max_length=191)
    shipping_address: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    billing_address: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    logistics_provider: Optional[int] = None
    delivery_fee: Optional[float] = None
    delivery_time: Optional[str] = Field(max_length=191)
    order_status: OrderStatus = Field(default=OrderStatus.ORDER_PENDING)
    payment_status: PaymentStatus = Field(default=PaymentStatus.PAYMENT_PENDING)
    deleted_at: Optional[datetime] = None
    fullfillment_id: Optional[int] = Field(
        foreign_key="users.id", nullable=True
    )  # Foreign key to users
    assign_date: Optional[datetime] = None

    # relationships
    customer: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Order.customer_id"}
    )
    shop: Optional["Shop"] = Relationship(back_populates="orders")
    # parent: "Order" = Relationship(remote_side=[id])
    order_products: List["OrderProduct"] = Relationship(back_populates="order")
    fulfillment_user: Optional["User"] = Relationship(
        back_populates="fulfillment_orders",
        sa_relationship_kwargs={"foreign_keys": "Order.fullfillment_id"},
    )


class OrderCreate(SQLModel):
    tracking_number: str
    customer_contact: str
    amount: float
    customer_id: Optional[int] = None
    shop_id: Optional[int] = None
    fullfillment_id: Optional[int] = None  # Can be null


class OrderRead(TimeStampReadModel):
    id: int
    tracking_number: str
    amount: float
    order_status: OrderStatus
    payment_status: PaymentStatus
    customer_id: Optional[int]
    shop_id: Optional[int]
    fullfillment_id: Optional[int]


# class OrderReadWithRelations(OrderRead):
#     customer: Optional["UserReadBase"] = None
#     shop: Optional["ShopRead"] = None
#     fulfillment_user: Optional["UserReadBase"] = None


class OrderUpdate(SQLModel):
    order_status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    delivery_time: Optional[str] = None
    fullfillment_id: Optional[int] = None  # Can update fulfillment user
    assign_date: Optional[datetime] = None
