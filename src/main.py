from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel
from fastapi.middleware.cors import CORSMiddleware
from src.api.core.middleware.error_handling import register_exception_handlers
from src.api.routers.attribute import (
    attributeRoute,
    attributeValueRoute,
    attributeProductRoute,
)
from .lib.db_con import engine

from src.api.routers import (
    # user
    authRoute,
    userRoute,
    # role
    roleRoute,
    userRoleRoute,
    # shop
    shopRoute,
    userShopRoute,
    # category
    categoryRoute,
    # product
    productRoute,
    # media
    uploadMediaRoute,
    # cart
    cartRoute,
    # wishlist
    wishlistRoute,
    # manufacturer
    manufacturerRoute,
    # shipping
    shippingRoute,
    # banner
    bannerRoute,
    # Email Template
    emailRoute,
    # order
    orderRoute,
    # Review
    reviewRoute,
    # Address
    addressRoute,
    # coupon
    couponRoute,
)


# Define app lifespan — this runs once when the app starts and when it shuts down
@asynccontextmanager
async def lifespan(app: FastAPI):
    # # --- Runs once on startup ---
    # print("🟢 Checking if tables exist...")

    # # Create all tables that are missing (safe – only creates non-existent ones)
    # SQLModel.metadata.create_all(engine)
    # print("✅ All tables verified / created.")
    # # --- Runs once on shutdown ---
    # print("🔴 App shutting down...")

    yield  # 👈 after this, FastAPI starts handling requests


# Initialize the FastAPI app with the custom lifespan
app = FastAPI(lifespan=lifespan, root_path="/api")
# Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://admin-ctspk.vercel.app",
        "https://ctspk-frontend.vercel.app",
        "http://localhost:3000",
    ],  # or "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Hello, FastAPI with uv!"}


app.include_router(authRoute.router)
app.include_router(uploadMediaRoute.router)
app.include_router(userRoute.router)
# role
app.include_router(roleRoute.router)
app.include_router(userRoleRoute.router)
# Shop
app.include_router(shopRoute.router)
app.include_router(userShopRoute.router)
# Category
app.include_router(categoryRoute.router)
# Product
app.include_router(productRoute.router)
# Attribute
app.include_router(attributeRoute.router)
app.include_router(attributeValueRoute.router)
app.include_router(attributeProductRoute.router)
# Cart
app.include_router(cartRoute.router)
# wishlist
app.include_router(wishlistRoute.router)
# Manufacturer
app.include_router(manufacturerRoute.router)
# Banner
app.include_router(bannerRoute.router)
# Shipping
app.include_router(shippingRoute.router)
# Email Template
app.include_router(emailRoute.router)
# Order
app.include_router(orderRoute.router)
# Review
app.include_router(reviewRoute.router)
# Address
app.include_router(addressRoute.router)
# Coupon
app.include_router(couponRoute.router)
