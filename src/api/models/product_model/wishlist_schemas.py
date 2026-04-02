# src/api/models/product_model/wishlist_schemas.py
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel


class CategoryReadForWishlist(SQLModel):
    id: int
    name: str
    slug: str
    root_id: int
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


class ShopReadForWishlist(SQLModel):
    id: int
    name: Optional[str] = None
    is_active: Optional[bool] = None


class ManufacturerReadForWishlist(SQLModel):
    id: int
    name: str
    is_active: Optional[bool] = None


class ProductReadForWishlist(SQLModel):
    id: int
    name: str
    price: Optional[float] = None
    sale_price: Optional[float] = None
    image: Optional[Dict[str, Any]] = None
    quantity: Optional[int] = None
    in_stock: bool = True
    shop_id: int
    slug: str
    category: Optional[CategoryReadForWishlist] = None
    shop: Optional[ShopReadForWishlist] = None
    manufacturer: Optional[ManufacturerReadForWishlist] = None


class WishlistReadWithProduct(SQLModel):
    id: int
    user_id: int
    product_id: int
    variation_option_id: Optional[int] = None
    product: Optional[ProductReadForWishlist] = None
    created_at: datetime