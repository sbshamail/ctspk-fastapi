# src/api/models/product_model/wishlist_schemas.py
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel


class ProductReadForWishlist(SQLModel):
    id: int
    name: str
    price: Optional[float] = None
    sale_price: Optional[float] = None
    image: Optional[Dict[str, Any]] = None
    in_stock: bool = True
    slug: str


class WishlistReadWithProduct(SQLModel):
    id: int
    user_id: int
    product_id: int
    variation_option_id: Optional[int] = None
    product: Optional[ProductReadForWishlist] = None
    created_at: datetime