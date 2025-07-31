from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    image_alt_text: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    price: float
    stock_quantity: int

class ProductCreate(ProductBase):
    # Make description and image_url required for creation
    description: str
    image_url: str
    
class Product(ProductBase):
    id: int
    created_at: datetime # Assuming products also have a creation timestamp
    updated_at: Optional[datetime] = None # Assuming products can also have an update timestamp

    class Config:
        from_attributes = True
