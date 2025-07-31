import os
import mysql.connector
from typing import Dict, Any

def get_db_config() -> Dict[str, Any]:
    """Get database configuration from environment variables"""
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "user": os.getenv("MYSQL_USER", "app_user"),
        "password": os.getenv("MYSQL_PASSWORD", "changeme123"),
        "database": os.getenv("MYSQL_DATABASE", "shopping_website"),
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
        "autocommit": True
    }

def get_db_connection():
    """Get a database connection using environment configuration"""
    try:
        config = get_db_config()
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        raise
