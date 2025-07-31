# backend/app/main.py

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api import product_api, auth, customer_api, order_api, cart_api, favorites_api, ml_api
from app.dependencies import get_current_user
from app.models.user import User

app = FastAPI(title="Shopping Website API")

# Add CORS middleware to allow frontend to access backend resources
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501", "*"],  # Allow frontend origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Mount static files (for product images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include the API routers
app.include_router(product_api.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(customer_api.router, prefix="/api/v1")
app.include_router(order_api.router, prefix="/api/v1")
app.include_router(cart_api.router, prefix="/api/v1")
app.include_router(favorites_api.router, prefix="/api/v1")
app.include_router(ml_api.router, prefix="/api/v1")  # ML API endpoints

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Shopping Website API!"}

@app.get("/api/v1/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Returns the details of the currently authenticated user.
    This endpoint requires a valid JWT access token.
    """
    return current_user

