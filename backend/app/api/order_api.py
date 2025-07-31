# backend/app/api/order_api.py

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.dependencies import get_current_user
from app.models.user import User
from app.models.order import Order, OrderCreate, OrderItem # Import OrderItem too for responses
from app.repositories.order_repository import OrderRepository
import mysql.connector # For specific database error handling

router = APIRouter()
order_repo = OrderRepository()

# --- TEMP Order Management Endpoints ---
@router.post("/orders/temp/add_item")
async def add_item_to_temp_order(item: dict, current_user: User = Depends(get_current_user)):
    """
    Add or update an item in the user's TEMP order. Creates TEMP order if none exists.
    item: {product_id: int, quantity: int}
    """
    try:
        result = order_repo.add_or_update_temp_item(user_id=current_user.id, product_id=item["product_id"], quantity=item["quantity"])
        return {"success": True, "order": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/orders/temp/remove_item")
async def remove_item_from_temp_order(item: dict, current_user: User = Depends(get_current_user)):
    """
    Remove an item from the user's TEMP order.
    item: {product_id: int}
    """
    try:
        result = order_repo.remove_temp_item(user_id=current_user.id, product_id=item["product_id"])
        return {"success": True, "order": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/orders/temp/close")
async def close_temp_order(current_user: User = Depends(get_current_user)):
    """
    Close (purchase) the user's TEMP order.
    """
    try:
        result = order_repo.close_temp_order(user_id=current_user.id)
        return {"success": True, "order": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/orders/temp")
async def delete_temp_order(current_user: User = Depends(get_current_user)):
    """
    Delete the user's TEMP order.
    """
    try:
        result = order_repo.delete_temp_order(user_id=current_user.id)
        return {"success": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/orders", response_model=List[Order])
async def get_all_orders_api():
    try:
        orders_data = order_repo.get_all_orders()
        return orders_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch orders: {e}")

@router.get("/orders/user", response_model=List[Order])
async def get_user_orders_api(current_user: User = Depends(get_current_user)):
    """Get all orders for the current authenticated user."""
    try:
        orders_data = order_repo.get_orders_by_user_id(current_user.id)
        return orders_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch user orders: {e}")

@router.get("/orders/{order_id}", response_model=Order)
async def get_order_api(order_id: int):
    try:
        order = order_repo.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order with ID {order_id} not found.")
        return order
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch order: {e}")

@router.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order_api(order_create: OrderCreate):
    try:
        # The total_amount calculation and stock deduction happen in the repository for atomicity
        new_order = order_repo.create_order(
            customer_id=order_create.customer_id,
            items_data=[item.model_dump() for item in order_create.items] # Convert Pydantic models to dicts
        )
        if not new_order:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve new order after creation.")
        return new_order
    except ValueError as e:
        # Catch specific business logic errors like "Product not found" or "Insufficient stock"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except mysql.connector.Error as e:
        # Catch database-related errors (e.g., customer_id foreign key violation)
        if e.errno == 1452: # MySQL error for foreign key constraint fail
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid customer_id or product_id in order items.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error during order creation: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create order: {e}")

@router.put("/orders/{order_id}/status", response_model=Order) # Specific endpoint for status update
async def update_order_status_api(order_id: int, status_update: dict): # Use a simple dict for status update payload
    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'status' field is required.")
    
    # You might want to define a list of valid statuses (e.g., "PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED")
    valid_statuses = ["PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]
    if new_status.upper() not in valid_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: '{new_status}'. Valid statuses are: {', '.join(valid_statuses)}")

    try:
        updated_order = order_repo.update_order_status(order_id, new_status.upper())
        if not updated_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order with ID {order_id} not found.")
        return updated_order
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update order status: {e}")

@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order_api(order_id: int):
    try:
        deleted = order_repo.delete_order(order_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order with ID {order_id} not found.")
        return
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete order: {e}")
