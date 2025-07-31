from fastapi import APIRouter, HTTPException, status
from typing import List, Optional

from app.models.product import Product, ProductCreate
from app.repositories.product_repository import ProductRepository
import mysql.connector # For specific error handling if needed

router = APIRouter()
product_repo = ProductRepository()

@router.get("/products", response_model=List[Product])
async def get_all_products_api():
    try:
        products_data = product_repo.get_all_products()
        return products_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch products: {e}")

@router.get("/products/{product_id}", response_model=Product)
async def get_product_api(product_id: int):
    try:
        product = product_repo.get_product_by_id(product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found.")
        return product
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch product: {e}")

@router.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product_api(product: ProductCreate):
    try:
        new_product_data = product_repo.create_product(
            name=product.name,
            description=product.description,
            image_url=product.image_url,
            image_alt_text=product.image_alt_text,
            category=product.category,
            brand=product.brand,
            price=product.price,
            stock_quantity=product.stock_quantity
        )
        if not new_product_data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve new product after insertion.")
        return new_product_data
    except mysql.connector.IntegrityError as err:
        # Assuming product name might need to be unique, if not, remove this part
        if err.errno == 1062:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Product with name '{product.name}' already exists.")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database integrity error: {err}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create product: {e}")

@router.put("/products/{product_id}", response_model=Product)
async def update_product_api(product_id: int, product: ProductCreate): # ProductCreate can serve as update payload
    try:
        updated_product = product_repo.update_product(
            product_id=product_id,
            name=product.name,
            description=product.description,
            image_url=product.image_url,
            image_alt_text=product.image_alt_text,
            category=product.category,
            brand=product.brand,
            price=product.price,
            stock_quantity=product.stock_quantity
        )
        if not updated_product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found or no changes made.")
        return updated_product
    except mysql.connector.IntegrityError as err:
        # Again, if product name is unique, handle conflict
        if err.errno == 1062:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Product with name '{product.name}' already exists.")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database integrity error during update: {err}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update product: {e}")

@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_api(product_id: int):
    try:
        deleted = product_repo.delete_product(product_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found.")
        return
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete product: {e}")
