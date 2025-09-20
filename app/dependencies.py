"""
FastAPI dependencies for authentication and database access
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.shared.database import get_db
from app.user_management.user_service import UserService
from app.user_management.user_models import User
from app.shared.exceptions import AuthenticationError, UserNotFoundError

# Security scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user
    """
    try:
        token_data = UserService.verify_token(credentials.credentials)
        user = UserService.get_user_by_id(db, token_data.user_id)
        return user
    except (AuthenticationError, UserNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get the current authenticated and active user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to optionally get the current user (for endpoints that work with or without auth)
    """
    if not credentials:
        return None

    try:
        token_data = UserService.verify_token(credentials.credentials)
        user = UserService.get_user_by_id(db, token_data.user_id)
        return user if user.is_active else None
    except (AuthenticationError, UserNotFoundError):
        return None


def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to get the current authenticated admin user
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user