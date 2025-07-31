import mysql.connector
from typing import List, Dict, Any, Optional
from datetime import datetime

# IMPORTANT: Use your actual database credentials from docker-compose.yml
import mysql.connector
from typing import Dict, List, Optional, Any
from app.database import get_db_connection # Use centralized database configuration

class ProductRepository:
    def __init__(self):
        pass

    def _get_db_connection(self):
        """Get database connection using secure configuration"""
        return get_db_connection()

    def get_all_products(self) -> List[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, name, description, image_url, image_alt_text, category, brand, price, stock_quantity, created_at, updated_at FROM product")
            products = cursor.fetchall()
            for product in products:
                if isinstance(product.get('created_at'), datetime):
                    product['created_at'] = product['created_at'].isoformat()
                if isinstance(product.get('updated_at'), datetime):
                    product['updated_at'] = product['updated_at'].isoformat()
            return products
        finally:
            cursor.close()
            conn.close()

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, name, description, image_url, image_alt_text, category, brand, price, stock_quantity, created_at, updated_at FROM product WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            if product:
                if isinstance(product.get('created_at'), datetime):
                    product['created_at'] = product['created_at'].isoformat()
                if isinstance(product.get('updated_at'), datetime):
                    product['updated_at'] = product['updated_at'].isoformat()
            return product
        finally:
            cursor.close()
            conn.close()

    def create_product(self, name: str, description: str, image_url: str, image_alt_text: Optional[str] = None, 
                      category: Optional[str] = None, brand: Optional[str] = None, price: float = 0.0, stock_quantity: int = 0) -> Dict[str, Any]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "INSERT INTO product (name, description, image_url, image_alt_text, category, brand, price, stock_quantity) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            values = (name, description, image_url, image_alt_text, category, brand, price, stock_quantity)
            cursor.execute(sql, values)
            conn.commit()

            product_id = cursor.lastrowid
            cursor.execute("SELECT id, name, description, image_url, image_alt_text, category, brand, price, stock_quantity, created_at, updated_at FROM product WHERE id = %s", (product_id,))
            new_product = cursor.fetchone()

            if new_product:
                if isinstance(new_product.get('created_at'), datetime):
                    new_product['created_at'] = new_product['created_at'].isoformat()
                if isinstance(new_product.get('updated_at'), datetime):
                    new_product['updated_at'] = new_product['updated_at'].isoformat()

            return new_product
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()

    def update_product(self, product_id: int, name: str, description: Optional[str], image_url: Optional[str] = None, 
                      image_alt_text: Optional[str] = None, category: Optional[str] = None, brand: Optional[str] = None, 
                      price: float = 0.0, stock_quantity: int = 0) -> Optional[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "UPDATE product SET name = %s, description = %s, image_url = %s, image_alt_text = %s, category = %s, brand = %s, price = %s, stock_quantity = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            values = (name, description, image_url, image_alt_text, category, brand, price, stock_quantity, product_id)
            cursor.execute(sql, values)
            conn.commit()

            if cursor.rowcount == 0:
                return None # Product not found or no changes made

            return self.get_product_by_id(product_id)
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()

    def delete_product(self, product_id: int) -> bool:
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM product WHERE id = %s", (product_id,))
            conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()
