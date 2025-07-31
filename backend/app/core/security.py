# backend/app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional
import os

from passlib.context import CryptContext
from jose import JWTError, jwt

# --- Password Hashing ---
# This is where you configure Passlib to use the bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain-text password."""
    return pwd_context.hash(password)

# --- JWT (JSON Web Token) Configuration ---
# Get JWT secret from environment variables for security
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-key-change-in-production-very-long-secret-key-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # How long the access token will be valid

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# No verify_token function here for now, as FastAPI's security dependencies
# will handle the token verification. We will use a dependency later.
