"""Test app for cart endpoints - bypasses the emoji encoding issue in main.py"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import cartRoute, authRoute

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Test Cart API"}

app.include_router(authRoute.router)
app.include_router(cartRoute.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
