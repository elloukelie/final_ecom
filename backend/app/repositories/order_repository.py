# backend/app/repositories/order_repository.py

import mysql.connector
from typing import List, Dict, Any, Optional
from datetime import datetime
import math # For handling floating point comparisons if needed
from app.database import get_db_connection # Use centralized database configuration

class OrderRepository:
    # --- TEMP Order Management Methods ---
    def add_or_update_temp_item(self, user_id: int, product_id: int, quantity: int):
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            conn.start_transaction()
            
            # First, get the customer_id for this user_id
            cursor.execute("SELECT id FROM customer WHERE user_id = %s", (user_id,))
            customer_record = cursor.fetchone()
            if not customer_record:
                raise ValueError(f"No customer record found for user ID {user_id}")
            customer_id = customer_record['id']
            
            # Get product info and validate
            cursor.execute("SELECT id, name, price, stock_quantity FROM product WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            if not product:
                raise ValueError(f"Product with ID {product_id} not found.")
            if product['stock_quantity'] < quantity:
                raise ValueError(f"Not enough stock for {product['name']}. Available: {product['stock_quantity']}, Requested: {quantity}")
            
            # Find or create TEMP order for customer
            cursor.execute("SELECT id FROM `order` WHERE customer_id = %s AND status = 'TEMP'", (customer_id,))
            temp_order = cursor.fetchone()
            
            if not temp_order:
                # Create new TEMP order
                cursor.execute("INSERT INTO `order` (customer_id, total_amount, status) VALUES (%s, %s, 'TEMP')", 
                             (customer_id, 0.0))
                order_id = cursor.lastrowid
            else:
                order_id = temp_order['id']
            
            # Check if item already exists in order
            cursor.execute("SELECT id, quantity FROM order_item WHERE order_id = %s AND product_id = %s", 
                         (order_id, product_id))
            existing_item = cursor.fetchone()
            
            if existing_item:
                # Update existing item
                cursor.execute("UPDATE order_item SET quantity = %s, price_at_order = %s WHERE id = %s",
                             (quantity, product['price'], existing_item['id']))
            else:
                # Add new item
                cursor.execute("INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES (%s, %s, %s, %s)",
                             (order_id, product_id, quantity, product['price']))
            
            # Recalculate total_amount
            cursor.execute("SELECT SUM(quantity * price_at_order) as total FROM order_item WHERE order_id = %s", (order_id,))
            total = cursor.fetchone()['total'] or 0.0
            cursor.execute("UPDATE `order` SET total_amount = %s WHERE id = %s", (total, order_id))
            
            conn.commit()
            return self.get_order_by_id(order_id)
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def remove_temp_item(self, user_id: int, product_id: int):
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            conn.start_transaction()
            
            # First, get the customer_id for this user_id
            cursor.execute("SELECT id FROM customer WHERE user_id = %s", (user_id,))
            customer_record = cursor.fetchone()
            if not customer_record:
                raise ValueError(f"No customer record found for user ID {user_id}")
            customer_id = customer_record['id']
            
            # Find TEMP order for customer
            cursor.execute("SELECT id FROM `order` WHERE customer_id = %s AND status = 'TEMP'", (customer_id,))
            temp_order = cursor.fetchone()
            if not temp_order:
                raise ValueError("No TEMP order found for user.")
            
            order_id = temp_order['id']
            
            # Remove item from order
            cursor.execute("DELETE FROM order_item WHERE order_id = %s AND product_id = %s", 
                         (order_id, product_id))
            
            if cursor.rowcount == 0:
                raise ValueError("Item not found in order.")
            
            # Check if any items left
            cursor.execute("SELECT COUNT(*) as count FROM order_item WHERE order_id = %s", (order_id,))
            item_count = cursor.fetchone()['count']
            
            if item_count == 0:
                # Delete empty order
                cursor.execute("DELETE FROM `order` WHERE id = %s", (order_id,))
                conn.commit()
                return None
            else:
                # Recalculate total_amount
                cursor.execute("SELECT SUM(quantity * price_at_order) as total FROM order_item WHERE order_id = %s", (order_id,))
                total = cursor.fetchone()['total'] or 0.0
                cursor.execute("UPDATE `order` SET total_amount = %s WHERE id = %s", (total, order_id))
                
                conn.commit()
                return self.get_order_by_id(order_id)
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def close_temp_order(self, user_id: int):
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            conn.start_transaction()
            
            # First, get the customer_id for this user_id
            cursor.execute("SELECT id FROM customer WHERE user_id = %s", (user_id,))
            customer_record = cursor.fetchone()
            if not customer_record:
                raise ValueError(f"No customer record found for user ID {user_id}")
            customer_id = customer_record['id']
            
            # Find TEMP order for customer
            cursor.execute("SELECT id FROM `order` WHERE customer_id = %s AND status = 'TEMP'", (customer_id,))
            temp_order = cursor.fetchone()
            if not temp_order:
                raise ValueError("No TEMP order found for user.")
            
            order_id = temp_order['id']
            
            # Get all items in the order
            cursor.execute("SELECT product_id, quantity FROM order_item WHERE order_id = %s", (order_id,))
            items = cursor.fetchall()
            
            if not items:
                raise ValueError("Cannot close empty order.")
            
            # Deduct stock for each item
            for item in items:
                cursor.execute("SELECT stock_quantity, name FROM product WHERE id = %s FOR UPDATE", (item['product_id'],))
                product = cursor.fetchone()
                if not product:
                    raise ValueError(f"Product {item['product_id']} not found.")
                
                new_stock = product['stock_quantity'] - item['quantity']
                if new_stock < 0:
                    raise ValueError(f"Insufficient stock for {product['name']}.")
                
                cursor.execute("UPDATE product SET stock_quantity = %s WHERE id = %s", 
                             (new_stock, item['product_id']))
            
            # Update order status to CLOSE
            cursor.execute("UPDATE `order` SET status = 'CLOSE' WHERE id = %s", (order_id,))
            
            conn.commit()
            return self.get_order_by_id(order_id)
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def delete_temp_order(self, user_id: int):
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            # First, get the customer_id for this user_id
            cursor.execute("SELECT id FROM customer WHERE user_id = %s", (user_id,))
            customer_record = cursor.fetchone()
            if not customer_record:
                return False  # No customer record found
            customer_id = customer_record[0]
            
            # Find TEMP order for customer
            cursor.execute("SELECT id FROM `order` WHERE customer_id = %s AND status = 'TEMP'", (customer_id,))
            temp_order = cursor.fetchone()
            if not temp_order:
                return False  # No TEMP order found
            
            order_id = temp_order[0]  # Not using dictionary=True for this cursor
            
            # Delete order (CASCADE will delete order_items automatically)
            cursor.execute("DELETE FROM `order` WHERE id = %s", (order_id,))
            conn.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def _get_db_connection(self):
        """Get database connection using secure configuration"""
        return get_db_connection()

    def _format_order_data(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to format datetime objects for API response."""
        if order_data:
            if isinstance(order_data.get('order_date'), datetime):
                order_data['order_date'] = order_data['order_date'].isoformat()
        return order_data

    def _format_order_item_data(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to format order item data for API response."""
        # No datetime for order_item itself, but keep consistent with formatting helpers
        return item_data

    def get_all_orders(self) -> List[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Fetch all orders with customer information
            cursor.execute("""
                SELECT o.id, o.customer_id, o.order_date, o.total_amount, o.status,
                       c.first_name, c.last_name, c.phone, c.address
                FROM `order` o 
                JOIN customer c ON o.customer_id = c.id
                ORDER BY o.order_date DESC
            """)
            orders = [self._format_order_data(order) for order in cursor.fetchall()]

            # For each order, fetch its items and format customer info
            for order in orders:
                cursor.execute("SELECT id, order_id, product_id, quantity, price_at_order FROM order_item WHERE order_id = %s", (order['id'],))
                order['items'] = [self._format_order_item_data(item) for item in cursor.fetchall()]
                
                # Add customer shipping information
                order['customer_info'] = {
                    'name': f"{order['first_name']} {order['last_name']}",
                    'phone': order.get('phone', 'Not provided'),
                    'address': order.get('address', 'Not provided')
                }
                
                # Remove the individual customer fields since we have customer_info
                order.pop('first_name', None)
                order.pop('last_name', None)
                order.pop('phone', None)
                order.pop('address', None)
                
            return orders
        finally:
            cursor.close()
            conn.close()

    def get_orders_by_user_id(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all orders for a specific user by user_id."""
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # First get the customer info for this user
            cursor.execute("SELECT id, first_name, last_name, phone, address FROM customer WHERE user_id = %s", (user_id,))
            customer_result = cursor.fetchone()
            if not customer_result:
                return []  # No customer record for this user
            
            customer_id = customer_result['id']
            
            # Fetch all orders for this customer
            cursor.execute("SELECT id, customer_id, order_date, total_amount, status FROM `order` WHERE customer_id = %s ORDER BY order_date DESC", (customer_id,))
            orders = [self._format_order_data(order) for order in cursor.fetchall()]

            # For each order, fetch its items and add customer info
            for order in orders:
                cursor.execute("SELECT id, order_id, product_id, quantity, price_at_order FROM order_item WHERE order_id = %s", (order['id'],))
                order['items'] = [self._format_order_item_data(item) for item in cursor.fetchall()]
                
                # Add customer shipping information
                order['customer_info'] = {
                    'name': f"{customer_result['first_name']} {customer_result['last_name']}",
                    'phone': customer_result.get('phone', 'Not provided'),
                    'address': customer_result.get('address', 'Not provided')
                }
            return orders
        finally:
            cursor.close()
            conn.close()

    def get_order_by_id(self, order_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Fetch the order with customer information
            cursor.execute("""
                SELECT o.id, o.customer_id, o.order_date, o.total_amount, o.status,
                       c.first_name, c.last_name, c.phone, c.address
                FROM `order` o 
                JOIN customer c ON o.customer_id = c.id
                WHERE o.id = %s
            """, (order_id,))
            order = self._format_order_data(cursor.fetchone())

            if order:
                # Fetch its items
                cursor.execute("SELECT id, order_id, product_id, quantity, price_at_order FROM order_item WHERE order_id = %s", (order_id,))
                order['items'] = [self._format_order_item_data(item) for item in cursor.fetchall()]
                
                # Add customer shipping information
                order['customer_info'] = {
                    'name': f"{order['first_name']} {order['last_name']}",
                    'phone': order['phone'],
                    'address': order['address']
                }
            return order
        finally:
            cursor.close()
            conn.close()

    def create_order(self, customer_id: int, items_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True) # Use dictionary=True for fetching data
        try:
            conn.start_transaction() # Start a transaction for atomicity

            total_amount = 0.0
            processed_items = []
            
            # 1. Validate products and calculate total_amount, reduce stock
            for item in items_data:
                product_id = item['product_id']
                quantity = item['quantity']

                # Get product details including current price and stock
                cursor.execute("SELECT id, name, price, stock_quantity FROM product WHERE id = %s FOR UPDATE", (product_id,)) # Lock row
                product = cursor.fetchone()

                if not product:
                    raise ValueError(f"Product with ID {product_id} not found.")
                if product['stock_quantity'] < quantity:
                    raise ValueError(f"Insufficient stock for product '{product['name']}'. Available: {product['stock_quantity']}, Requested: {quantity}")

                # Calculate item price and add to total
                price_at_order = float(product['price']) # Ensure float for calculation
                item_total = price_at_order * quantity
                total_amount += item_total
                
                # Store product details for order item insertion
                processed_items.append({
                    "product_id": product_id,
                    "quantity": quantity,
                    "price_at_order": price_at_order,
                    "product_name": product['name'] # For better error messages/logging if needed
                })

                # Reduce stock
                new_stock = product['stock_quantity'] - quantity
                cursor.execute("UPDATE product SET stock_quantity = %s WHERE id = %s", (new_stock, product_id))

            # 2. Create the main order
            sql_order = "INSERT INTO `order` (customer_id, total_amount, status) VALUES (%s, %s, %s)"
            order_values = (customer_id, total_amount, "PENDING")
            cursor.execute(sql_order, order_values)
            order_id = cursor.lastrowid
            
            if not order_id:
                raise Exception("Failed to create order, no ID returned.")

            # 3. Create order items
            sql_order_item = "INSERT INTO order_item (order_id, product_id, quantity, price_at_order) VALUES (%s, %s, %s, %s)"
            order_item_values = []
            for item in processed_items:
                order_item_values.append((order_id, item['product_id'], item['quantity'], item['price_at_order']))
            
            if order_item_values: # Only execute if there are items
                cursor.executemany(sql_order_item, order_item_values)

            conn.commit() # Commit the transaction

            # Fetch the newly created order with its items for the response
            return self.get_order_by_id(order_id)

        except mysql.connector.Error as err:
            conn.rollback() # Rollback on any database error
            raise err
        except ValueError as err: # Catch custom validation errors
            conn.rollback()
            raise err
        except Exception as err: # Catch any other unexpected errors
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()

    def update_order_status(self, order_id: int, new_status: str) -> Optional[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "UPDATE `order` SET status = %s WHERE id = %s"
            values = (new_status, order_id)
            cursor.execute(sql, values)
            conn.commit()

            if cursor.rowcount == 0:
                return None # Order not found or no changes made

            return self.get_order_by_id(order_id)
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()

    def delete_order(self, order_id: int) -> bool:
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            # Due to ON DELETE CASCADE on order_item, deleting the order will
            # automatically delete its associated order items.
            cursor.execute("DELETE FROM `order` WHERE id = %s", (order_id,))
            conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()
