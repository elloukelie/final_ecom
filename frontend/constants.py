# backend/app/constants.py
import os

# FastAPI Backend URL for API calls (internal Docker network)
BACKEND_API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_BASE_URL = f"{BACKEND_API_URL}/api/v1"

# Backend URL for browser-accessible resources (images, static files)
# In Docker, this should be localhost:8000 so browser can access it
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")

def get_image_url(image_path):
    """
    Convert relative image paths to full URLs accessible from browser
    """
    if not image_path or image_path.strip() == '' or image_path == 'None':
        return None
    
    # If it's already a full URL, return as is
    if image_path.startswith(('http://', 'https://')):
        return image_path
    
    # If it's a relative path starting with /static, prepend browser-accessible backend URL
    if image_path.startswith('/static'):
        return f"{BACKEND_BASE_URL}{image_path}"
    
    # Otherwise, return as is
    return image_path
