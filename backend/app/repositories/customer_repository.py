import mysql.connector
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.repositories.user_repository import UserRepository

# IMPORTANT: Use your actual database credentials from docker-compose.yml
import mysql.connector
from typing import Dict, List, Optional, Any
from app.repositories.user_repository import UserRepository
from app.database import get_db_connection # Use centralized database configuration

class CustomerRepository:
    def __init__(self):
        self.user_repository = UserRepository()

    def _get_db_connection(self):
        """Get database connection using secure configuration"""
        return get_db_connection()

    def get_all_customers(self) -> List[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Join with user table to get user information
            cursor.execute("""
                SELECT c.id, c.user_id, c.first_name, c.last_name, c.email, c.phone, c.address, c.created_at,
                       u.username, u.is_admin, u.is_active
                FROM customer c 
                JOIN user u ON c.user_id = u.id
            """)
            customers = cursor.fetchall()
            # Ensure datetime objects are handled correctly by Pydantic
            for customer in customers:
                if isinstance(customer.get('created_at'), datetime):
                    customer['created_at'] = customer['created_at'].isoformat()
            return customers
        finally:
            cursor.close()
            conn.close()

    def create_customer(self, username: str, password: str, first_name: str, last_name: str, email: str = None, phone: str = None, address: str = None) -> Dict[str, Any]:
        """Create a customer with an associated user account"""
        # First create the user account
        user = self.user_repository.create_user(username, password, email)
        
        # Then create the customer record
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "INSERT INTO customer (user_id, first_name, last_name, email, phone, address) VALUES (%s, %s, %s, %s, %s, %s)"
            values = (user['id'], first_name, last_name, email, phone, address)
            cursor.execute(sql, values)
            conn.commit()
            customer_id = cursor.lastrowid
            
            # Return the new customer with user information
            return self.get_customer_by_id(customer_id)
        except mysql.connector.Error as err:
            conn.rollback()
            # If customer creation fails, we should also delete the user account
            try:
                self.user_repository.delete_user(user['id'])
            except:
                pass  # If user deletion also fails, log it but don't raise
            raise err
        finally:
            cursor.close()
            conn.close()

    def get_customer_by_id(self, customer_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Join with user table to get user information
            cursor.execute("""
                SELECT c.id, c.user_id, c.first_name, c.last_name, c.email, c.phone, c.address, c.created_at,
                       u.username, u.is_admin, u.is_active
                FROM customer c 
                JOIN user u ON c.user_id = u.id
                WHERE c.id = %s
            """, (customer_id,))
            customer = cursor.fetchone()
            if customer and isinstance(customer.get('created_at'), datetime):
                customer['created_at'] = customer['created_at'].isoformat()
            return customer
        finally:
            cursor.close()
            conn.close()

    def get_customer_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get customer by user_id"""
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT c.id, c.user_id, c.first_name, c.last_name, c.email, c.phone, c.address, c.created_at,
                       u.username, u.is_admin, u.is_active
                FROM customer c 
                JOIN user u ON c.user_id = u.id
                WHERE c.user_id = %s
            """, (user_id,))
            customer = cursor.fetchone()
            if customer and isinstance(customer.get('created_at'), datetime):
                customer['created_at'] = customer['created_at'].isoformat()
            return customer
        finally:
            cursor.close()
            conn.close()

    def update_customer(self, customer_id: int, first_name: str, last_name: str, email: str = None, phone: str = None, address: str = None) -> Optional[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "UPDATE customer SET first_name = %s, last_name = %s, email = %s, phone = %s, address = %s WHERE id = %s"
            values = (first_name, last_name, email, phone, address, customer_id)
            cursor.execute(sql, values)
            conn.commit()
            
            if cursor.rowcount == 0: # Check if any row was actually updated
                return None
            
            # Return the updated customer
            return self.get_customer_by_id(customer_id)
        finally:
            cursor.close()
            conn.close()

    def update_customer_shipping(self, user_id: int, first_name: str = None, last_name: str = None, 
                               phone: str = None, address: str = None) -> bool:
        """Update customer shipping information by user_id"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            # Build dynamic update query
            updates = []
            values = []
            
            if first_name is not None:
                updates.append("first_name = %s")
                values.append(first_name)
            if last_name is not None:
                updates.append("last_name = %s")
                values.append(last_name)
            if phone is not None:
                updates.append("phone = %s")
                values.append(phone)
            if address is not None:
                updates.append("address = %s")
                values.append(address)
            
            if not updates:
                return True  # Nothing to update
            
            values.append(user_id)  # Add user_id for WHERE clause
            
            query = f"UPDATE customer SET {', '.join(updates)} WHERE user_id = %s"
            cursor.execute(query, values)
            conn.commit()
            
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def delete_customer(self, customer_id: int) -> bool:
        """Delete customer and associated user account"""
        # Get customer info to find the user_id before deletion
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            return False
            
        user_id = customer['user_id']
        
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            conn.start_transaction()
            
            # Delete the customer record (this will cascade due to foreign key)
            cursor.execute("DELETE FROM customer WHERE id = %s", (customer_id,))
            customer_deleted = cursor.rowcount > 0
            
            # Delete the associated user account
            if customer_deleted:
                cursor.execute("DELETE FROM user WHERE id = %s", (user_id,))
                user_deleted = cursor.rowcount > 0
                
                if user_deleted:
                    conn.commit()
                    return True
                else:
                    conn.rollback()
                    return False
            else:
                conn.rollback()
                return False
                
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()
