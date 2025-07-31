# backend/app/models/customer.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CustomerBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    username: str  # Required for creating the associated user account
    password: str  # Required for creating the associated user account

class Customer(CustomerBase):
    id: int
    user_id: int  # Link to the user account
    created_at: datetime
    
    class Config:
        from_attributes = True
