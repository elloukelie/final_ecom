# import mysql.connector
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.core.security import get_password_hash # Import password hashing utility
from app.database import get_db_connection # Use centralized database configurationepositories/user_repository.py

import mysql.connector
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.security import get_password_hash # Import password hashing utility

# IMPORTANT: Use your actual database credentials from docker-compose.yml
DB_CONFIG = {
    "host": "127.0.0.1", # Ensure this matches your local setup
    "user": "user",
    "password": "password",
    "database": "shopping_website"
}

class UserRepository:
    def __init__(self):
        pass

    def _get_db_connection(self):
        """Get database connection using secure configuration"""
        return get_db_connection()

    def _format_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to format datetime objects for API response."""
        if user_data and isinstance(user_data.get('created_at'), datetime):
            user_data['created_at'] = user_data['created_at'].isoformat()
        return user_data

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, username, password_hash, email, is_active, is_admin, created_at FROM `user` WHERE username = %s", (username,))
            user = self._format_user_data(cursor.fetchone())
            return user
        finally:
            cursor.close()
            conn.close()

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, username, password_hash, email, is_active, is_admin, created_at FROM `user` WHERE id = %s", (user_id,))
            user = self._format_user_data(cursor.fetchone())
            return user
        finally:
            cursor.close()
            conn.close()

    def create_user(self, username: str, password: str, email: Optional[str] = None) -> Dict[str, Any]:
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            hashed_password = get_password_hash(password) # Hash the password
            
            sql = "INSERT INTO `user` (username, password_hash, email) VALUES (%s, %s, %s)"
            values = (username, hashed_password, email)
            cursor.execute(sql, values)
            conn.commit()

            user_id = cursor.lastrowid
            
            # Fetch the newly created user for the response
            new_user = self.get_user_by_id(user_id)
            if not new_user:
                raise Exception("Failed to retrieve new user after creation.")
            
            # Remove password_hash before returning to API
            new_user.pop("password_hash", None)
            return new_user
        except mysql.connector.IntegrityError as err:
            conn.rollback()
            if err.errno == 1062: # Duplicate entry error (e.g., duplicate username or email)
                if "username" in err.msg:
                    raise ValueError(f"Username '{username}' already exists.")
                elif "email" in err.msg and email:
                    raise ValueError(f"Email '{email}' already registered.")
                else:
                    raise ValueError(f"Duplicate entry error: {err.msg}")
            raise err
        except Exception as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()

    # You can add other CRUD methods for users if needed (update, delete),
    # but for authentication, get_user_by_username and create_user are primary.

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address"""
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, username, email, is_active, created_at FROM `user` WHERE email = %s", (email,))
            user = cursor.fetchone()
            return user
        except mysql.connector.Error as err:
            raise err
        finally:
            cursor.close()
            conn.close()

    def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM `user` WHERE id = %s", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()

    def delete_user_by_email(self, email: str) -> bool:
        """Delete a user by email address"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM `user` WHERE email = %s", (email,))
            conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users for admin management"""
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, username, email, is_active, is_admin, created_at FROM `user` ORDER BY created_at DESC")
            users = cursor.fetchall()
            return [self._format_user_data(user) for user in users]
        finally:
            cursor.close()
            conn.close()

    def update_user_admin_status(self, user_id: int, is_admin: bool) -> bool:
        """Update admin status for a user"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE `user` SET is_admin = %s WHERE id = %s", (is_admin, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()

    def update_user_active_status(self, user_id: int, is_active: bool) -> bool:
        """Update active status for a user"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE `user` SET is_active = %s WHERE id = %s", (is_active, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()
