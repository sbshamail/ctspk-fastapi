from typing import TYPE_CHECKING, Literal, Optional, List
from pydantic import BaseModel
from sqlmodel import Field, Relationship, UniqueConstraint
from src.api.models.product_model.productsModel import ProductRead
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel


if TYPE_CHECKING:
    from src.api.models import Product


class Cart(TimeStampedModel, table=True):
    __tablename__: Literal["carts"] = "carts"
    # ✅ Unique constraint: one product per user
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uix_user_product"),
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


class CartRead(CartBase, TimeStampReadModel):
    id: int
    product: ProductRead
    variation_option_id: Optional[int] = None


class CartBulkResponse(BaseModel):
    success_count: int
    failed_count: int
    failed_items: List[dict]
    message: str