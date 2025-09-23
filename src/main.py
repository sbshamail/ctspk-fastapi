from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel
from fastapi.middleware.cors import CORSMiddleware
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
    uploadImageRoute,
)


# Define app lifespan — this runs once when the app starts and when it shuts down
@asynccontextmanager
async def lifespan(app: FastAPI):

    yield  # 👈 after this, FastAPI starts handling requests


# Initialize the FastAPI app with the custom lifespan
app = FastAPI(lifespan=lifespan)
app = FastAPI(root_path="/api")

# Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 Allow all domains
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)


@app.get("/")
def root():
    return {"message": "Hello, FastAPI with uv!"}


app.include_router(authRoute.router)
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
app.include_router(uploadImageRoute.router)
