# backend/app/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.security import SECRET_KEY, ALGORITHM
from app.repositories.user_repository import UserRepository
from app.models.user import User

# OAuth2PasswordBearer will be used to extract the token from the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")

user_repo = UserRepository()

# Dependency to get the current user from the token
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user_data = user_repo.get_user_by_username(username)
    if user_data is None:
        raise credentials_exception
    
    # Exclude password_hash before returning the User model
    user_data.pop("password_hash", None) 
    return User(**user_data)
