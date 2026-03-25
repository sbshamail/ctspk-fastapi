from typing import TYPE_CHECKING, Literal, Optional, List
from pydantic import BaseModel
from sqlmodel import Field, Relationship, UniqueConstraint
from src.api.models.product_model.productsModel import ProductRead
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel


if TYPE_CHECKING:
    from src.api.models import Product


class Cart(TimeStampedModel, table=True):
    __tablename__: Literal["carts"] = "carts"
    # ✅ Unique constraint: one product + variation per user
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", "variation_option_id", name="uix_user_product_variation"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id")
    user_id: int = Field(foreign_key="users.id")
    shop_id: int = Field(foreign_key="shops.id")
    quantity: int = Field(default=1, ge=1)
    variation_option_id: Optional[int] = Field(
        default=None, foreign_key="variation_options.id"
    )

    # Relationships
    product: "Product" = Relationship(back_populates="carts")


class CartBase(BaseModel):
    product_id: int
    shop_id: int
    quantity: int
    variation_option_id: Optional[int] = None

class CartCreate(CartBase):
    pass


class CartBulkCreate(BaseModel):
    items: List[CartCreate]


class CartUpdate(BaseModel):
    quantity: Optional[int] = Field(default=1, ge=1)


class CartQuantityUpdate(BaseModel):
    """Request model for PATCH updatecart endpoint"""
    quantity: int = Field(ge=1)
    variation_option_id: Optional[int] = None


class CartDeleteRequest(BaseModel):
    """Request model for DELETE cart endpoints"""
    variation_option_id: Optional[int] = None


class CartDeleteItem(BaseModel):
    """Single item for delete-many endpoint"""
    product_id: int
    variation_option_id: Optional[int] = None


class CartDeleteManyRequest(BaseModel):
    """Request model for DELETE delete-many endpoint"""
    items: List[CartDeleteItem]


class CartRead(CartBase, TimeStampReadModel):
    id: int
    product: ProductRead
    variation_option_id: Optional[int] = None


class CartBulkResponse(BaseModel):
    success:int
    success_count: int
    failed_count: int
    failed_items: List[dict]
    message: str


# New models for cart/my-cart, cart/add, cart/bulk-add responses
class CategoryForCart(BaseModel):
    """Category info for cart item"""
    id: int
    name: str
    slug: str
    is_active: Optional[bool] = None


class ShopForCart(BaseModel):
    """Shop info for cart item"""
    id: int
    name: str
    slug: str
    is_active: Optional[bool] = None


class ManufacturerForCart(BaseModel):
    """Manufacturer info for cart item"""
    id: int
    name: str
    slug: Optional[str] = None
    is_active: Optional[bool] = None


class CartItemResponse(BaseModel):
    """Response model for a single cart item with product details"""
    product_id: int
    shop_id: int
    quantity: int
    variation_option_id: Optional[int] = None
    title: str
    unit_price: float
    original_price: float
    discount: float
    imageUrl: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[CategoryForCart] = None
    shop: Optional[ShopForCart] = None
    manufacturer_id: Optional[int] = None
    manufacturer: Optional[ManufacturerForCart] = None


class MyCartResponse(BaseModel):
    """Response model for cart/my-cart endpoint"""
    success: int
    data: List[CartItemResponse]


class AddCartResponse(BaseModel):
    """Response model for cart/add endpoint"""
    success: int
    data: CartItemResponse


class BulkAddCartRequest(BaseModel):
    """Request model for cart/bulk-add endpoint"""
    items: List[CartBase]


class BulkAddCartResponse(BaseModel):
    """Response model for cart/bulk-add endpoint"""
    success: int
    data: List[CartItemResponse]