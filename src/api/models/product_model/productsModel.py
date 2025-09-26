from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, List
from datetime import datetime
from sqlmodel import JSON, Column, SQLModel, Field, Relationship
from enum import Enum

from src.api.models.shop_model.shopsModel import ShopRead
from src.api.models.category_model.categoryModel import CategoryRead
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import Shop, Category


class ProductStatus(str, Enum):
    PUBLISH = "publish"
    DRAFT = "draft"


class ProductType(str, Enum):
    SIMPLE = "simple"
    VARIABLE = "variable"


class Product(TimeStampedModel, table=True):
    __tablename__: Literal["products"] = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=191)
    slug: str = Field(max_length=191)
    description: Optional[str] = None
    price: Optional[float] = None
    is_active: bool = Field(default=True)

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
    unit: str = Field(default=None, max_length=191)

    height: Optional[float] = Field(default=None, max_length=191)  # in cm
    width: Optional[float] = Field(default=None, max_length=191)
    length: Optional[float] = Field(default=None, max_length=191)
    dimension_unit: Optional[str] = Field(default=None, max_length=10, nullable=True)

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
    # foriegn key
    category_id: int = Field(foreign_key="categories.id")
    shop_id: Optional[int] = Field(foreign_key="shops.id")
    # author_id: Optional[int] = Field(foreign_key="authors.id")
    # manufacturer_id: Optional[int] = Field(foreign_key="manufacturers.id")

    # relationships
    shop: Optional["Shop"] = Relationship(back_populates="products")
    category: Optional["Category"] = Relationship(back_populates="products")

    # categories: List["CategoryProduct"] = Relationship(back_populates="product")
    # variation_options: List["VariationOption"] = Relationship(back_populates="product")


class ProductCreate(SQLModel):
    name: str
    slug: str
    description: str
    image: Optional[Dict[str, Any]] = None
    gallery: Optional[List[Dict[str, Any]]] = None
    category_id: int
    price: float
    max_price: float
    min_price: float
    shop_id: int = None


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    category_id: int = None
    image: Optional[Dict[str, Any]] = None
    gallery: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None
    price: Optional[float] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    shop_id: Optional[int] = None
    unit: Optional[str] = None


class UserReadForProduct(TimeStampReadModel):
    id: int
    name: str


class ShopReadForProduct(TimeStampReadModel):
    id: int
    name: Optional[str] = None
    # include nested owner
    owner: Optional[UserReadForProduct] = None

    model_config = {"from_attributes": True}


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
    image: Optional[Dict[str, Any]] = None
    gallery: Optional[List[Dict[str, Any]]] = None
    is_active: bool
    quantity: int
    status: ProductStatus
    product_type: ProductType
    category: CategoryRead
    shop: ShopReadForProduct
    unit: Optional[str] = None
