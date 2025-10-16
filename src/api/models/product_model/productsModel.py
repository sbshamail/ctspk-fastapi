from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, List
from datetime import datetime
from pydantic import BaseModel
from sqlmodel import JSON, Column, SQLModel, Field, Relationship
from enum import Enum

from src.api.models.shop_model.shopsModel import ShopRead
from src.api.models.category_model.categoryModel import CategoryRead
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import (
        Shop,
        Category,
        Cart,
        Manufacturer,
        VariationOption,
        Wishlist,
        OrderProduct,
        Review,
        ReturnItem,
        ProductPurchase,
    )


class ProductStatus(str, Enum):
    PUBLISH = "publish"
    DRAFT = "draft"


class ProductType(str, Enum):
    SIMPLE = "simple"
    VARIABLE = "variable"
    GROUPED = "grouped"




class Product(TimeStampedModel, table=True):
    __tablename__: Literal["products"] = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191)
    slug: str = Field(max_length=191, index=True, unique=True)
    description: Optional[str] = None
    price: Optional[float] = None
    is_active: bool = Field(default=True)
    weight: Optional[float] = Field(default=None, max_length=191)
    sale_price: Optional[float] = None
    purchase_price: Optional[float] = None
    language: str = Field(default="en", max_length=191)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sku: Optional[str] = Field(max_length=191)
    bar_code: Optional[str] = Field(max_length=250)
    quantity: int = Field(default=0)
    in_stock: bool = Field(default=True)
    is_taxable: bool = Field(default=False)

    status: ProductStatus = Field(default=ProductStatus.PUBLISH)
    product_type: ProductType = Field(default=ProductType.SIMPLE)
    unit: Optional[str] = Field(default=None, max_length=191)
    warranty: Optional[str]
    meta_title: Optional[str] = Field(default=None, max_length=250)
    meta_description: Optional[str]
    return_policy: Optional[str]
    shipping_info: Optional[str]

    tags: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON),
    )

    height: Optional[float] = Field(default=None, max_length=191)
    width: Optional[float] = Field(default=None, max_length=191)
    length: Optional[float] = Field(default=None, max_length=191)
    dimension_unit: Optional[str] = Field(default=None, max_length=30, nullable=True)
    is_feature: Optional[bool] = Field(default=None)

    image: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
    )
    video: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
    )

    gallery: Optional[List[Dict[str, Any]]] = Field(sa_column=Column(JSON))
    deleted_at: Optional[datetime] = None
    is_digital: bool = Field(default=False)
    is_external: bool = Field(default=False)
    external_product_url: Optional[str] = Field(max_length=191)
    external_product_button_text: Optional[str] = Field(max_length=191)

    # For variable products - store attributes as JSON
    attributes: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        sa_column=Column(JSON),
    )

    # ADDED: Track total purchased quantity
    total_purchased_quantity: int = Field(default=0)
    # ADDED: Track total sold quantity
    total_sold_quantity: int = Field(default=0)

    # foreign key
    category_id: int = Field(foreign_key="categories.id", index=True)
    shop_id: Optional[int] = Field(foreign_key="shops.id", index=True)
    manufacturer_id: Optional[int] = Field(
        foreign_key="manufacturers.id", index=True, default=None
    )

    # relationships
    shop: Optional["Shop"] = Relationship(back_populates="products")
    category: Optional["Category"] = Relationship(back_populates="products")
    carts: Optional[list["Cart"]] = Relationship(back_populates="product")
    manufacturer: Optional["Manufacturer"] = Relationship(back_populates="products")
    variation_options: List["VariationOption"] = Relationship(back_populates="product")
    order_products: List["OrderProduct"] = Relationship(back_populates="product")
    wishlists: Optional["Wishlist"] = Relationship(back_populates="product")
    reviews: Optional["Review"] = Relationship(back_populates="product")
    product_purchases: List["ProductPurchase"] = Relationship(back_populates="product")


class ProductAttributeValue(SQLModel):
    id: int
    value: str
    meta: Optional[str] = None


class ProductAttribute(SQLModel):
    id: int
    name: str
    values: List[ProductAttributeValue]
    selected_values: Optional[List[int]] = None
    is_visible: bool = True
    is_variation: bool = True


class VariationData(SQLModel):
    id: Optional[str] = None
    attributes: List[Dict[str, Any]]
    price: float
    sale_price: Optional[float] = None
    purchase_price: Optional[float] = None
    quantity: int
    sku: str
    bar_code: Optional[str] = None
    image: Optional[Dict[str, Any]] = None
    is_active: bool = True


class ProductCreate(SQLModel):
    name: str
    description: str
    image: Optional[Dict[str, Any]] = None
    gallery: Optional[List[Dict[str, Any]]] = None
    purchase_price: Optional[float] = None
    weight: Optional[float] = None
    category_id: int
    manufacturer_id: Optional[int] = None
    price: float
    sale_price: Optional[float] = None
    unit: str
    max_price: float
    min_price: float
    shop_id: int
    quantity: Optional[int] = None
    in_stock: Optional[bool] = None
    is_taxable: Optional[bool] = None
    is_feature: Optional[bool] = Field(default=False)
    height: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None
    dimension_unit: Optional[str] = None
    sku: Optional[str] = None
    warranty: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    return_policy: Optional[str] = None
    shipping_info: Optional[str] = None
    tags: Optional[List[str]] = None
    bar_code: Optional[str] = None
    product_type: ProductType = Field(default=ProductType.SIMPLE)
    status: ProductStatus = Field(default=ProductStatus.PUBLISH)
    attributes: Optional[List[ProductAttribute]] = None
    variations: Optional[List[VariationData]] = None


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    is_active: Optional[bool] = True
    category_id: Optional[int] = None
    manufacturer_id: Optional[int] = None
    image: Optional[Dict[str, Any]] = None
    gallery: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None
    price: Optional[float] = None
    sale_price: Optional[float] = None
    purchase_price: Optional[float] = None
    weight: Optional[float] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    shop_id: Optional[int] = None
    unit: Optional[str] = None
    is_feature: Optional[bool] = Field(default=False)
    quantity: Optional[int] = None
    in_stock: Optional[bool] = None
    is_taxable: Optional[bool] = None
    height: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None
    dimension_unit: Optional[str] = None
    sku: Optional[str] = None
    warranty: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    return_policy: Optional[str] = None
    shipping_info: Optional[str] = None
    tags: Optional[List[str]] = None
    bar_code: Optional[str] = None
    product_type: Optional[ProductType] = None
    status: Optional[ProductStatus] = None
    attributes: Optional[List[ProductAttribute]] = None
    variations: Optional[List[VariationData]] = None


class ProductActivate(SQLModel):
    is_active: bool


class UserReadForProduct(SQLModel):
    id: int
    name: str


class ShopReadForProduct(SQLModel):
    id: int
    name: Optional[str] = None


class CategoryReadProduct(SQLModel):
    id: int
    name: str
    slug: str
    root_id: int
    parent_id: Optional[int] = None


class VariationOptionReadForProduct(SQLModel):
    id: int
    title: str
    price: str
    sale_price: Optional[str] = None
    purchase_price: Optional[float] = None
    quantity: int
    options: Dict[str, Any]
    image: Optional[Dict[str, Any]] = None
    sku: Optional[str] = None
    bar_code: Optional[str] = None
    is_active: bool


class ProductRead(TimeStampReadModel):
    id: int
    name: str
    description: Optional[str] = None
    slug: str
    price: float
    sale_price: Optional[float] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    purchase_price: Optional[float] = None
    weight: Optional[float] = None
    image: Optional[Dict[str, Any]] = None
    gallery: Optional[List[Dict[str, Any]]] = None
    is_active: bool
    is_feature: Optional[bool] = None
    quantity: int
    status: ProductStatus
    product_type: ProductType
    category: CategoryReadProduct
    shop: ShopReadForProduct
    manufacturer_id: Optional[int] = None
    unit: Optional[str] = None
    dimension_unit: Optional[str] = None
    sku: Optional[str] = None
    height: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None
    warranty: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    return_policy: Optional[str] = None
    shipping_info: Optional[str] = None
    tags: Optional[List[str]] = None
    bar_code: Optional[str] = None
    attributes: Optional[List[ProductAttribute]] = None
    variations: Optional[List[VariationOptionReadForProduct]] = None
    variations_count: Optional[int] = 0
    total_quantity: Optional[int] = 0
    # ADDED: Purchase and sales tracking
    total_purchased_quantity: int = 0
    total_sold_quantity: int = 0
    current_stock_value: Optional[float] = None


class ProductListRead(TimeStampReadModel):
    id: int
    name: str
    description: Optional[str] = None
    slug: str
    price: float
    sale_price: Optional[float] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    purchase_price: Optional[float] = None
    weight: Optional[float] = None
    image: Optional[Dict[str, Any]] = None
    is_active: bool
    is_feature: Optional[bool] = None
    quantity: int
    category: CategoryReadProduct
    shop: ShopReadForProduct
    manufacturer_id: Optional[int] = None
    warranty: Optional[str] = None
    shipping_info: Optional[str] = None
