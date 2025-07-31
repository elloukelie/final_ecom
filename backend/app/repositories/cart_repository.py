# backend/app/repositories/cart_repository.py

import mysql.connector
from typing import List, Dict, Any, Optional
from app.database import get_db_connection # Use centralized database configuration

class CartRepository:
    def _get_db_connection(self):
        """Get database connection using secure configuration"""
        return get_db_connection()

    def get_cart_items(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all cart items for a user"""
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
            SELECT c.id, c.user_id, c.product_id, c.quantity, c.created_at, c.updated_at,
                   p.name, p.description, p.price, p.stock_quantity, p.image_url, p.category, p.brand
            FROM cart c
            JOIN product p ON c.product_id = p.id
            WHERE c.user_id = %s
            ORDER BY c.updated_at DESC
            """
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def add_or_update_cart_item(self, user_id: int, product_id: int, quantity: int) -> bool:
        """Add item to cart or update quantity if it exists"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if item already exists in cart
            cursor.execute("SELECT id, quantity FROM cart WHERE user_id = %s AND product_id = %s", 
                         (user_id, product_id))
            existing_item = cursor.fetchone()
            
            if existing_item:
                # Update existing item quantity
                cursor.execute("UPDATE cart SET quantity = %s WHERE user_id = %s AND product_id = %s", 
                             (quantity, user_id, product_id))
            else:
                # Add new item to cart
                cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)", 
                             (user_id, product_id, quantity))
            
            conn.commit()
            return True
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Error adding/updating cart item: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def remove_cart_item(self, user_id: int, product_id: int) -> bool:
        """Remove item from cart"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM cart WHERE user_id = %s AND product_id = %s", 
                         (user_id, product_id))
            conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Error removing cart item: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def clear_cart(self, user_id: int) -> bool:
        """Clear all items from user's cart"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
            conn.commit()
            return True
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Error clearing cart: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_cart_count(self, user_id: int) -> int:
        """Get total number of items in cart"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT SUM(quantity) FROM cart WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return result[0] if result[0] else 0
        finally:
            cursor.close()
            conn.close()

    def get_cart_total(self, user_id: int) -> float:
        """Get total price of items in cart"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            query = """
            SELECT SUM(c.quantity * p.price) as total
            FROM cart c
            JOIN product p ON c.product_id = p.id
            WHERE c.user_id = %s
            """
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            return float(result[0]) if result[0] else 0.0
        finally:
            cursor.close()
            conn.close()
