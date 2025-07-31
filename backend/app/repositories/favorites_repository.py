# backend/app/repositories/favorites_repository.py

import mysql.connector
from typing import List, Dict, Any, Optional
from app.database import get_db_connection # Use centralized database configuration

class FavoritesRepository:
    def _get_db_connection(self):
        """Get database connection using secure configuration"""
        return get_db_connection()

    def get_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all favorite products for a user"""
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
            SELECT f.id, f.user_id, f.product_id, f.created_at,
                   p.name, p.description, p.price, p.stock_quantity, p.image_url, p.category, p.brand
            FROM favorites f
            JOIN product p ON f.product_id = p.id
            WHERE f.user_id = %s
            ORDER BY f.created_at DESC
            """
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def add_favorite(self, user_id: int, product_id: int) -> bool:
        """Add product to favorites"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO favorites (user_id, product_id) VALUES (%s, %s)", 
                         (user_id, product_id))
            conn.commit()
            return True
        except mysql.connector.IntegrityError:
            # Item already in favorites
            return True
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Error adding favorite: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def remove_favorite(self, user_id: int, product_id: int) -> bool:
        """Remove product from favorites"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM favorites WHERE user_id = %s AND product_id = %s", 
                         (user_id, product_id))
            conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Error removing favorite: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def is_favorite(self, user_id: int, product_id: int) -> bool:
        """Check if product is in user's favorites"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM favorites WHERE user_id = %s AND product_id = %s", 
                         (user_id, product_id))
            return cursor.fetchone() is not None
        finally:
            cursor.close()
            conn.close()

    def get_favorites_count(self, user_id: int) -> int:
        """Get count of favorite products for a user"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM favorites WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        finally:
            cursor.close()
            conn.close()

    def clear_favorites(self, user_id: int) -> bool:
        """Clear all favorites for a user"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM favorites WHERE user_id = %s", (user_id,))
            conn.commit()
            return True
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Error clearing favorites: {err}")
            return False
        finally:
            cursor.close()
            conn.close()
