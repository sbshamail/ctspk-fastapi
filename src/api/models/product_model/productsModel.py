from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, List
from datetime import datetime, timezone
from sqlmodel import JSON, Column, Enum, SQLModel, Field, Relationship

from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import Shop, Type, VariationOption, CategoryProduct


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
    unit: str = Field(max_length=191)
    height: Optional[str] = Field(max_length=191)
    width: Optional[str] = Field(max_length=191)
    length: Optional[str] = Field(max_length=191)
    image: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    video: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    gallery: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    deleted_at: Optional[datetime] = None
    is_digital: bool = Field(default=False)
    is_external: bool = Field(default=False)
    external_product_url: Optional[str] = Field(max_length=191)
    external_product_button_text: Optional[str] = Field(max_length=191)
    # foriegn key
    type_id: int = Field(foreign_key="types.id")
    shop_id: Optional[int] = Field(foreign_key="shops.id")
    author_id: Optional[int] = Field(foreign_key="authors.id")
    manufacturer_id: Optional[int] = Field(foreign_key="manufacturers.id")

    # ... rest of the product model code ...

    # relationships
    shop: Optional["Shop"] = Relationship(back_populates="products")
    type: "Type" = Relationship()
    categories: List["CategoryProduct"] = Relationship(back_populates="product")
    variation_options: List["VariationOption"] = Relationship(back_populates="product")


class ProductCreate(SQLModel):
    name: str
    slug: str
    type_id: int
    price: float
    shop_id: Optional[int] = None
    quantity: int = 0
    unit: str


class ProductRead(TimeStampReadModel):
    id: int
    name: str
    slug: str
    price: float
    quantity: int
    status: ProductStatus
    product_type: ProductType


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    status: Optional[ProductStatus] = None
