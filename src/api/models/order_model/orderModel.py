# src/api/models/orderModel.py
from typing import TYPE_CHECKING, Literal, Optional, List, Dict, Any
from sqlalchemy import Column, JSON, Text, Enum
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel
from enum import Enum as PyEnum


# Fulfillment user info schema
class FulfillmentUserInfo(SQLModel):
    id: int
    name: str
    email: str
    avatar: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

if TYPE_CHECKING:
    from src.api.models import (
        User,
        Shop,
        Product,
        VariationOption,
        Category,
        Review,
        ReturnItem,
        ReturnRequest,
        Tax,
        Shipping,
        Coupon
    )
    from src.api.models.orderReviewModel import OrderReview


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
    ORDER_DELIVER = "order-deliver"


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


class OrderItemType(str, PyEnum):
    SIMPLE = "simple"
    VARIABLE = "variable"


class Order(TimeStampedModel, table=True):
    __tablename__: Literal["orders"] = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    tracking_number: str = Field(max_length=191, unique=True)
    customer_id: Optional[int] = Field(default=None, foreign_key="users.id")
    customer_contact: str = Field(max_length=191)
    customer_name: Optional[str] = Field(max_length=191, default=None)
    amount: float = Field()  # Subtotal before any discounts/taxes
    sales_tax: Optional[float] = Field(default=None)  # Total sales tax
    paid_total: Optional[float] = Field(default=None)  # Final amount paid
    total: Optional[float] = Field(default=None)  # Final total after all calculations
    cancelled_amount: Decimal = Field(
        default=Decimal("0.00"), max_digits=10, decimal_places=2
    )
    admin_commission_amount: Decimal = Field(
        default=Decimal("0.00"), max_digits=10, decimal_places=2
    )
    language: str = Field(default="en", max_length=191)
    coupon_id: Optional[int] = Field(default=None, foreign_key="coupons.id")
    discount: Optional[float] = Field(default=None)  # Product discount total
    coupon_discount: Optional[float] = Field(default=None)  # NEW: Coupon discount amount
    payment_gateway: Optional[str] = Field(default=None, max_length=191)
    shipping_address: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    billing_address: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    logistics_provider: Optional[int] = Field(default=None)
    delivery_fee: Optional[float] = Field(default=None)
    delivery_time: Optional[str] = Field(default=None, max_length=191)
    order_status: Optional[str] = Field(default="order-pending")
    payment_status: Optional[str] = Field(default="payment-pending")

    fullfillment_id: Optional[int] = Field(default=None, foreign_key="users.id")
    assign_date: Optional[datetime] = Field(default=None)
    # NEW: Added tax_id and shipping_id foreign keys
    tax_id: Optional[int] = Field(default=None, foreign_key="tax_classes.id")
    shipping_id: Optional[int] = Field(default=None, foreign_key="shipping_classes.id")
    # Delivery proof images
    deliver_image: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    completed_image: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))

    # Order review reference
    order_review_id: Optional[int] = Field(default=None, foreign_key="order_reviews.id")

    # relationships
    customer: Optional["User"] = Relationship(
        back_populates="customer_orders",
        sa_relationship_kwargs={"foreign_keys": "[Order.customer_id]"},
    )

    fullfillment_user: Optional["User"] = Relationship(
        back_populates="fullfillment_orders",
        sa_relationship_kwargs={"foreign_keys": "[Order.fullfillment_id]"},
    )

    order_products: Optional[List["OrderProduct"]] = Relationship(
        back_populates="orders"
    )

    order_status_history: Optional["OrderStatus"] = Relationship(
        back_populates="orders",
        sa_relationship_kwargs={
            "foreign_keys": "[OrderStatus.order_id]",
            "uselist": False,
        },
    )
    reviews: Optional["Review"] = Relationship(back_populates="order")
    # NEW: Relationships for tax and shipping
    tax: Optional["Tax"] = Relationship()
    shipping: Optional["Shipping"] = Relationship()
    coupon: Optional["Coupon"] = Relationship()
    # Order review relationship
    order_review: Optional["OrderReview"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"foreign_keys": "[OrderReview.order_id]"}
    )

class OrderProduct(TimeStampedModel, table=True):
    __tablename__: Literal["order_product"] = "order_product"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    product_id: int = Field(foreign_key="products.id")
    variation_option_id: Optional[int] = Field(
        default=None, foreign_key="variation_options.id"
    )
    shop_id: Optional[int] = Field(default=None, foreign_key="shops.id")
    order_quantity: str = Field(max_length=191)
    admin_commission: Decimal = Field(
        default=Decimal("0.00"), max_digits=10, decimal_places=2
    )

    # ADDED: Fields for product type handling
    item_type: OrderItemType = Field(default=OrderItemType.SIMPLE)
    variation_data: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON)
    )  # Store variation attributes

    # ADDED: Product snapshot at time of order
    variation_snapshot: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))

    # ADDED: Review ID when review is added for this order item
    review_id: Optional[int] = Field(default=None, foreign_key="reviews.id")

    # ADDED: Return tracking fields
    return_request_id: Optional[int] = Field(default=None, foreign_key="return_requests.id")
    is_returned: bool = Field(default=False)
    returned_quantity: Optional[int] = Field(default=0)

    deleted_at: Optional[datetime] = None
    unit_price: float = Field()  # Original price
    sale_price: Optional[float] = Field(default=None)  # NEW: Sale price at time of order
    subtotal: float = Field()  # Final subtotal after product discount
    item_discount: Optional[float] = Field(default=0.0)  # NEW: Discount for this item
    item_tax: Optional[float] = Field(default=0.0)  # NEW: Tax for this item

    # relationships
    orders: "Order" = Relationship(back_populates="order_products")
    product: "Product" = Relationship(back_populates="order_products")
    variation_option: Optional["VariationOption"] = Relationship()
    shop: Optional["Shop"] = Relationship()


class OrderStatus(TimeStampedModel, table=True):
    __tablename__ = "orders_status"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", unique=True)
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
    order_deliver_date: Optional[datetime] = Field(default=None)

    orders: Optional["Order"] = Relationship(
        back_populates="order_status_history",
        sa_relationship_kwargs={"foreign_keys": "[OrderStatus.order_id]"},
    )


class OrderProductCreate(SQLModel):
    product_id: int
    variation_option_id: Optional[int] = None
    order_quantity: str
    unit_price: float
    subtotal: float
    item_type: OrderItemType = Field(default=OrderItemType.SIMPLE)
    variation_data: Optional[Dict[str, Any]] = None
    shop_id: Optional[int] = None


class CartItem(SQLModel):
    id: int = None  # cart id
    quantity: int
    product_id: int
    variation_option_id: Optional[int] = None  # ADDED for variable products
    
# For /cartcreate route - expects cart items in request
class OrderCartCreate(SQLModel):
    customer_contact: Optional[str] = None
    customer_name: Optional[str] = None
    payment_gateway: Optional[str] = None
    delivery_time: Optional[str] = None
    cart: List[CartItem]
    shipping_address: Optional[dict]
    billing_address: Optional[Dict[str, Any]] = None
    # NEW: Added tax_id, shipping_id, coupon_id for validation
    tax_id: Optional[int] = None
    shipping_id: Optional[int] = None
    coupon_id: Optional[int] = None

# For /create-from-cart route - gets cart items from cart table, no cart in request
class OrderFromCartCreate(SQLModel):
    shipping_address: Dict[str, Any]
    billing_address: Optional[Dict[str, Any]] = None
    payment_gateway: Optional[str] = None
    shipping_id: Optional[int] = None
    tax_id: Optional[int] = None
    coupon_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_id: Optional[int] = None
    delivery_time: Optional[str] = None

class OrderCreate(SQLModel):
    customer_id: Optional[int] = None
    customer_contact: Optional[str] = None
    customer_name: Optional[str] = None
    amount: float
    sales_tax: Optional[float] = None
    paid_total: Optional[float] = None
    total: Optional[float] = None
    discount: Optional[float] = None
    coupon_discount: Optional[float] = None  # NEW: Coupon discount field
    payment_gateway: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    logistics_provider: Optional[int] = None
    delivery_fee: Optional[float] = None
    delivery_time: Optional[str] = None
    payment_gateway: Optional[str] = None
    # NEW: Added required fields
    tax_id: Optional[int] = None
    shipping_id: Optional[int] = None
    coupon_id: Optional[int] = None
    order_products: List[OrderProductCreate]


class OrderUpdate(SQLModel):
    customer_id: Optional[int] = None
    customer_contact: Optional[str] = None
    customer_name: Optional[str] = None
    amount: Optional[float] = None
    sales_tax: Optional[float] = None
    paid_total: Optional[float] = None
    total: Optional[float] = None
    discount: Optional[float] = None
    coupon_discount: Optional[float] = None  # NEW: Coupon discount field
    payment_gateway: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    logistics_provider: Optional[int] = None
    delivery_fee: Optional[float] = None
    delivery_time: Optional[str] = None
    # NEW: Added tax and shipping fields
    tax_id: Optional[int] = None
    shipping_id: Optional[int] = None
    coupon_id: Optional[int] = None
    order_status: Optional[OrderStatusEnum] = None
    payment_status: Optional[PaymentStatusEnum] = None
    fullfillment_id: Optional[int] = None
    assign_date: Optional[datetime] = None


class OrderStatusUpdate(SQLModel):
    order_status: Optional[OrderStatusEnum] = None
    payment_status: Optional[PaymentStatusEnum] = None
    deliver_image: Optional[List[Dict[str, Any]]] = None  # Required for OUT_FOR_DELIVERY (step 6)
    completed_image: Optional[List[Dict[str, Any]]] = None  # Required for ORDER_DELIVER (step 7)


class ProductOrderRead(SQLModel):
    image: Optional[Dict[str, Any]] = None
    name: str


# Read Schemas - UPDATED
class OrderProductRead(TimeStampReadModel):
    id: int
    order_id: int
    product_id: int
    product: ProductOrderRead
    variation_option_id: Optional[int] = None
    order_quantity: str
    unit_price: float
    sale_price: Optional[float] = None  # NEW: Sale price field
    subtotal: float
    item_discount: Optional[float] = None  # NEW: Item discount field
    item_tax: Optional[float] = None  # NEW: Item tax field
    admin_commission: Decimal
    item_type: OrderItemType
    variation_data: Optional[Dict[str, Any]] = None
    product_snapshot: Optional[Dict[str, Any]] = None
    variation_snapshot: Optional[Dict[str, Any]] = None
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    shop_slug: Optional[str] = None
    review_id: Optional[int] = None
    # Return tracking fields
    return_request_id: Optional[int] = None
    is_returned: bool = False
    returned_quantity: Optional[int] = 0


class OrderRead(TimeStampReadModel):
    id: int
    tracking_number: str
    customer_id: Optional[int] = None
    customer_contact: Optional[str] = None
    customer_name: Optional[str] = None
    amount: float
    sales_tax: Optional[float] = None
    paid_total: Optional[float] = None
    total: Optional[float] = None
    cancelled_amount: Decimal
    admin_commission_amount: Decimal
    language: str
    coupon_id: Optional[int] = None
    discount: Optional[float] = None
    coupon_discount: Optional[float] = None  # NEW: Coupon discount field
    payment_gateway: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    logistics_provider: Optional[int] = None
    delivery_fee: Optional[float] = None
    delivery_time: Optional[str] = None
    # NEW: Added tax and shipping fields
    tax_id: Optional[int] = None
    shipping_id: Optional[int] = None
    order_status: OrderStatusEnum
    payment_status: PaymentStatusEnum
    fullfillment_id: Optional[int] = None
    assign_date: Optional[datetime] = None
    fullfillment_user_info: Optional[FulfillmentUserInfo] = None  # NEW: Fulfillment user info
    shops: Optional[List[Dict[str, Any]]] = None
    shop_count: Optional[int] = None
    deliver_image: Optional[List[Dict[str, Any]]] = None
    completed_image: Optional[List[Dict[str, Any]]] = None
    order_review_id:  Optional[int] = None


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
    order_deliver_date: Optional[datetime] = None
