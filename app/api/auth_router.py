"""
Authentication API endpoints
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.user_management.auth_schemas import UserCreate, UserLogin, Token, UserResponse, PasswordUpdate
from app.user_management.user_service import UserService
from app.shared.exceptions import (
    AuthenticationError,
    DuplicateUserError,
    UserNotFoundError,
    ValidationError
)
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.config import settings
from app.shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Register new user", description="Create a new user account with username, email, and password")
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user account"""
    try:
        user = UserService.create_user(db, user_data)
        logger.info("User registration successful", user_id=str(user.id))
        return user
    except DuplicateUserError as e:
        logger.warning("Registration failed - duplicate user", error=e.message)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": e.error_code,
                "message": e.message,
                "details": e.details
            }
        )
    except ValidationError as e:
        logger.warning("Registration failed - validation error", error=e.message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": e.error_code,
                "message": e.message,
                "details": e.details
            }
        )


@router.post("/login", response_model=Token,
             summary="User login", description="Authenticate user with username/email and password, returns JWT token")
def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token"""
    try:
        user = UserService.authenticate_user(db, login_data)

        # Create access token
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        access_token = UserService.create_access_token(
            data={"sub": user.username, "user_id": str(user.id)},
            expires_delta=access_token_expires
        )

        logger.info("User login successful", user_id=str(user.id))

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,  # Convert to seconds
            user_info=UserResponse.from_orm(user)
        )

    except AuthenticationError as e:
        logger.warning("Login failed", error=e.message, username=login_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": e.error_code,
                "message": e.message
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.get("/me", response_model=UserResponse,
            summary="Get current user", description="Retrieve current authenticated user information")
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@router.get("/status",
            summary="Get authentication status", description="Check if user is authenticated and get basic info")
def get_auth_status(current_user: User = Depends(get_current_active_user)):
    """Get authentication status and basic user info"""
    return {
        "authenticated": True,
        "user_id": str(current_user.id),
        "username": current_user.username,
        "is_active": current_user.is_active,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "account_created": current_user.created_at.isoformat()
    }


@router.put("/password", response_model=UserResponse)
def update_password(
    password_data: PasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user password"""
    try:
        user = UserService.update_user_password(
            db,
            str(current_user.id),
            password_data.current_password,
            password_data.new_password
        )
        logger.info("Password update successful", user_id=str(user.id))
        return user
    except AuthenticationError as e:
        logger.warning("Password update failed", user_id=str(current_user.id), error=e.message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": e.error_code,
                "message": e.message
            }
        )


@router.post("/logout",
             summary="User logout", description="Logout current user (client should discard the JWT token)")
def logout_user(current_user: User = Depends(get_current_active_user)):
    """Logout user (client should discard token)"""
    from datetime import datetime

    logger.info("User logout", user_id=str(current_user.id))
    return {
        "message": "Successfully logged out",
        "user_id": str(current_user.id),
        "logged_out_at": datetime.now().isoformat() + "Z"
    }


@router.post("/refresh", response_model=Token,
             summary="Refresh JWT token", description="Generate a new JWT token using current valid token")
def refresh_token(current_user: User = Depends(get_current_active_user)):
    """Refresh JWT token"""
    try:
        # Create new access token
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        access_token = UserService.create_access_token(
            data={"sub": current_user.username, "user_id": str(current_user.id)},
            expires_delta=access_token_expires
        )

        logger.info("Token refresh successful", user_id=str(current_user.id))

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user_info=UserResponse.from_orm(current_user)
        )
    except Exception as e:
        logger.error("Token refresh failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )