# backend/app/api/favorites_api.py

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.favorites_repository import FavoritesRepository

router = APIRouter()
favorites_repo = FavoritesRepository()

@router.get("/favorites")
async def get_favorites(current_user: User = Depends(get_current_user)):
    """Get all favorite products for the user"""
    try:
        favorites = favorites_repo.get_favorites(current_user.id)
        return {"success": True, "favorites": favorites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get favorites: {str(e)}")

@router.post("/favorites/add/{product_id}")
async def add_favorite(product_id: int, current_user: User = Depends(get_current_user)):
    """Add product to favorites"""
    try:
        success = favorites_repo.add_favorite(current_user.id, product_id)
        if success:
            return {"success": True, "message": "Product added to favorites"}
        else:
            raise HTTPException(status_code=500, detail="Failed to add to favorites")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add to favorites: {str(e)}")

@router.delete("/favorites/remove/{product_id}")
async def remove_favorite(product_id: int, current_user: User = Depends(get_current_user)):
    """Remove product from favorites"""
    try:
        success = favorites_repo.remove_favorite(current_user.id, product_id)
        if success:
            return {"success": True, "message": "Product removed from favorites"}
        else:
            raise HTTPException(status_code=404, detail="Product not found in favorites")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove from favorites: {str(e)}")

@router.post("/favorites/toggle/{product_id}")
async def toggle_favorite(product_id: int, current_user: User = Depends(get_current_user)):
    """Toggle product in favorites (add if not exists, remove if exists)"""
    try:
        is_favorite = favorites_repo.is_favorite(current_user.id, product_id)
        
        if is_favorite:
            success = favorites_repo.remove_favorite(current_user.id, product_id)
            message = "Product removed from favorites"
            action = "removed"
        else:
            success = favorites_repo.add_favorite(current_user.id, product_id)
            message = "Product added to favorites"
            action = "added"
        
        if success:
            return {"success": True, "message": message, "action": action, "is_favorite": not is_favorite}
        else:
            raise HTTPException(status_code=500, detail="Failed to toggle favorite")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle favorite: {str(e)}")

@router.get("/favorites/check/{product_id}")
async def check_favorite(product_id: int, current_user: User = Depends(get_current_user)):
    """Check if product is in user's favorites"""
    try:
        is_favorite = favorites_repo.is_favorite(current_user.id, product_id)
        return {"success": True, "is_favorite": is_favorite}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check favorite: {str(e)}")

@router.get("/favorites/count")
async def get_favorites_count(current_user: User = Depends(get_current_user)):
    """Get count of favorite products for the user"""
    try:
        count = favorites_repo.get_favorites_count(current_user.id)
        return {"success": True, "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get favorites count: {str(e)}")

@router.delete("/favorites/clear")
async def clear_favorites(current_user: User = Depends(get_current_user)):
    """Clear all favorites for the user"""
    try:
        success = favorites_repo.clear_favorites(current_user.id)
        if success:
            return {"success": True, "message": "All favorites cleared"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear favorites")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear favorites: {str(e)}")
