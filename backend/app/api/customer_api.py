from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional

from app.models.customer import Customer, CustomerCreate
from app.models.user import User
from app.dependencies import get_current_user
from app.repositories.customer_repository import CustomerRepository
import mysql.connector # For specific error handling

router = APIRouter()
customer_repo = CustomerRepository()

@router.get("/customers", response_model=List[Customer])
async def get_all_customers_api():
    try:
        customers_data = customer_repo.get_all_customers()
        return customers_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch customers: {e}")

@router.post("/customers", response_model=Customer, status_code=status.HTTP_201_CREATED)
async def create_customer_api(customer: CustomerCreate):
    try:
        new_customer_data = customer_repo.create_customer(
            username=customer.username,
            password=customer.password,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=customer.email,
            phone=customer.phone,
            address=customer.address
        )
        if not new_customer_data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve new customer after insertion.")
        return new_customer_data
    except mysql.connector.IntegrityError as err:
        if err.errno == 1062:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Customer with email '{customer.email}' or username '{customer.username}' already exists.")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database integrity error: {err}")
    except Exception as e: # Catch any other unexpected errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create customer: {e}")

@router.get("/customers/me", response_model=Customer)
async def get_current_customer_api(current_user: User = Depends(get_current_user)):
    """Get current user's customer information"""
    try:
        customer = customer_repo.get_customer_by_user_id(current_user.id)
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer record not found for current user.")
        return customer
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch customer: {e}")

@router.get("/customers/{customer_id}", response_model=Customer)
async def get_customer_api(customer_id: int):
    try:
        customer = customer_repo.get_customer_by_id(customer_id)
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer with ID {customer_id} not found.")
        return customer
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch customer: {e}")

@router.put("/customers/{customer_id}", response_model=Customer)
async def update_customer_api(customer_id: int, customer: CustomerCreate): # CustomerCreate can be used for update payload
    try:
        updated_customer = customer_repo.update_customer(
            customer_id=customer_id,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=customer.email,
            phone=customer.phone,
            address=customer.address
        )
        if not updated_customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer with ID {customer_id} not found or no changes made.")
        return updated_customer
    except mysql.connector.IntegrityError as err:
        if err.errno == 1062: # Duplicate entry error
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Customer with email '{customer.email}' already exists.")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database integrity error during update: {err}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update customer: {e}")

@router.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer_api(customer_id: int):
    try:
        deleted = customer_repo.delete_customer(customer_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer with ID {customer_id} not found.")
        # HTTP 204 No Content for successful deletion
        return
    except mysql.connector.IntegrityError as err:
        if err.errno == 1451:  # Foreign key constraint fails
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Cannot delete customer because they have existing orders. Please delete or reassign their orders first."
            )
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database integrity error during deletion: {err}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete customer: {e}")

@router.get("/customers/me", response_model=Customer)
async def get_current_customer_api(current_user: User = Depends(get_current_user)):
    """Get current user's customer information"""
    try:
        customer = customer_repo.get_customer_by_user_id(current_user.id)
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer record not found for current user.")
        return customer
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch customer: {e}")

@router.put("/customers/me/shipping")
async def update_shipping_info_api(shipping_data: dict, current_user: User = Depends(get_current_user)):
    """Update current user's shipping information"""
    try:
        success = customer_repo.update_customer_shipping(
            user_id=current_user.id,
            first_name=shipping_data.get('first_name'),
            last_name=shipping_data.get('last_name'),
            phone=shipping_data.get('phone'),
            address=shipping_data.get('address')
        )
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer record not found for current user.")
        return {"success": True, "message": "Shipping information updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update shipping info: {e}")

