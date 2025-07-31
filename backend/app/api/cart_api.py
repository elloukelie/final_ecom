# backend/app/api/cart_api.py

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.cart_repository import CartRepository

router = APIRouter()
cart_repo = CartRepository()

@router.get("/cart")
async def get_cart(current_user: User = Depends(get_current_user)):
    """Get all items in the user's cart"""
    try:
        cart_items = cart_repo.get_cart_items(current_user.id)
        return {"success": True, "items": cart_items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cart: {str(e)}")

@router.post("/cart/add")
async def add_to_cart(item: dict, current_user: User = Depends(get_current_user)):
    """Add item to cart
    item: {product_id: int, quantity: int}
    """
    try:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        
        if not product_id:
            raise HTTPException(status_code=400, detail="product_id is required")
        
        success = cart_repo.add_or_update_cart_item(current_user.id, product_id, quantity)
        if success:
            return {"success": True, "message": "Item added to cart"}
        else:
            raise HTTPException(status_code=500, detail="Failed to add item to cart")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add to cart: {str(e)}")

@router.post("/cart/update")
async def update_cart_item(item: dict, current_user: User = Depends(get_current_user)):
    """Update cart item quantity
    item: {product_id: int, quantity: int}
    """
    try:
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        
        if not product_id or quantity is None:
            raise HTTPException(status_code=400, detail="product_id and quantity are required")
        
        if quantity <= 0:
            # Remove item if quantity is 0 or negative
            success = cart_repo.remove_cart_item(current_user.id, product_id)
        else:
            success = cart_repo.add_or_update_cart_item(current_user.id, product_id, quantity)
        
        if success:
            return {"success": True, "message": "Cart updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update cart")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update cart: {str(e)}")

@router.delete("/cart/remove/{product_id}")
async def remove_from_cart(product_id: int, current_user: User = Depends(get_current_user)):
    """Remove item from cart"""
    try:
        success = cart_repo.remove_cart_item(current_user.id, product_id)
        if success:
            return {"success": True, "message": "Item removed from cart"}
        else:
            raise HTTPException(status_code=404, detail="Item not found in cart")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove from cart: {str(e)}")

@router.delete("/cart/clear")
async def clear_cart(current_user: User = Depends(get_current_user)):
    """Clear all items from cart"""
    try:
        success = cart_repo.clear_cart(current_user.id)
        if success:
            return {"success": True, "message": "Cart cleared"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear cart")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cart: {str(e)}")

@router.get("/cart/count")
async def get_cart_count(current_user: User = Depends(get_current_user)):
    """Get total number of items in cart"""
    try:
        count = cart_repo.get_cart_count(current_user.id)
        return {"success": True, "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cart count: {str(e)}")

@router.get("/cart/total")
async def get_cart_total(current_user: User = Depends(get_current_user)):
    """Get total price of items in cart"""
    try:
        total = cart_repo.get_cart_total(current_user.id)
        return {"success": True, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cart total: {str(e)}")
