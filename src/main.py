from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel
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
)


# Define app lifespan — this runs once when the app starts and when it shuts down
@asynccontextmanager
async def lifespan(app: FastAPI):

    yield  # 👈 after this, FastAPI starts handling requests


# Initialize the FastAPI app with the custom lifespan
app = FastAPI(lifespan=lifespan)


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
