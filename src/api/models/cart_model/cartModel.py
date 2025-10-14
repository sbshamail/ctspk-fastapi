from typing import TYPE_CHECKING, Literal, Optional
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

    # Relationships
    product: "Product" = Relationship(back_populates="carts")


class CartBase(BaseModel):
    product_id: int
    shop_id: int
    quantity: int


class CartCreate(CartBase):
    pass


class CartUpdate(BaseModel):
    quantity: Optional[int] = Field(default=1, ge=1)


class CartRead(CartBase, TimeStampReadModel):
    id: int
    user_id: int
    product: Optional[ProductRead] = None

    class Config:
        from_attributes = True
