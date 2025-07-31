# backend/app/api/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # For login endpoint
from datetime import timedelta

from pydantic import BaseModel

from app.models.user import User, UserCreate, UserLogin
from app.repositories.user_repository import UserRepository
from app.core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
import mysql.connector # For specific database error handling

router = APIRouter()
user_repo = UserRepository()

# Response model for token (standard for OAuth2)
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(user_create: UserCreate):
    try:
        # Check if user already exists
        db_user = user_repo.get_user_by_username(user_create.username)
        if db_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")
        
        # Import customer repository
        from app.repositories.customer_repository import CustomerRepository
        customer_repo = CustomerRepository()
        
        # Create customer with associated user account
        new_customer = customer_repo.create_customer(
            username=user_create.username,
            password=user_create.password,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            email=user_create.email,
            phone=user_create.phone,
            address=user_create.address
        )
        
        # Return the user part of the created customer
        new_user = user_repo.get_user_by_username(user_create.username)
        return new_user
    except ValueError as e: # Catch custom validation errors from repo (e.g., duplicate username/email)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register user: {e}")

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_data = user_repo.get_user_by_username(form_data.username)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password against hash
    if not verify_password(form_data.password, user_data["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # If user and password are valid, create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data["username"]}, # 'sub' (subject) is standard claim
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Admin Management Endpoints
from app.dependencies import get_current_user
from typing import List

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure only admin users can access admin endpoints"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.get("/admin/users", response_model=List[User])
async def get_all_users(admin_user: User = Depends(get_admin_user)):
    """Get all users - admin only"""
    try:
        users_data = user_repo.get_all_users()
        return users_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")

@router.put("/admin/users/{user_id}/admin-status")
async def update_user_admin_status(
    user_id: int, 
    is_admin: bool, 
    admin_user: User = Depends(get_admin_user)
):
    """Update admin status for a user - admin only"""
    try:
        # Prevent admin from removing their own admin status
        if user_id == admin_user.id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove admin status from yourself"
            )
        
        success = user_repo.update_user_admin_status(user_id, is_admin)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": f"User admin status {'granted' if is_admin else 'revoked'} successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update admin status: {str(e)}")

@router.put("/admin/users/{user_id}/active-status")
async def update_user_active_status(
    user_id: int, 
    is_active: bool, 
    admin_user: User = Depends(get_admin_user)
):
    """Update active status for a user - admin only"""
    try:
        # Prevent admin from deactivating themselves
        if user_id == admin_user.id and not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate yourself"
            )
        
        success = user_repo.update_user_active_status(user_id, is_active)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": f"User {'activated' if is_active else 'deactivated'} successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update active status: {str(e)}")
