# backend/app/models/order.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Customer Info Model ---
class CustomerInfo(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None

# --- Order Item Models ---
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    price_at_order: float = Field(..., description="Price of the product at the time the order was placed.")

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int # Unique ID for the order item itself
    order_id: int # Foreign key to the parent order
    class Config:
        from_attributes = True

# --- Order Models ---
class OrderBase(BaseModel):
    customer_id: int
    total_amount: float
    status: str = "PENDING" # Default status

class OrderCreate(OrderBase):
    items: List[OrderItemCreate] # When creating an order, you provide its items

class Order(OrderBase):
    id: int
    order_date: datetime # Renamed from created_at for clarity in orders
    items: List[OrderItem] = [] # Include the list of order items when retrieving an order
    customer_info: Optional[CustomerInfo] = None # Include customer shipping information

    class Config:
        from_attributes = True
