# backend/app/models/user.py

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None # Using EmailStr for email validation

class UserCreate(UserBase):
    password: str # Password needed for creation/registration
    first_name: str  # Required for customer record
    last_name: str   # Required for customer record
    phone: Optional[str] = None     # Optional customer info
    address: Optional[str] = None   # Optional customer info

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True # For Pydantic v2
