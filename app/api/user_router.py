"""
User management CRUD API endpoints
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, EmailStr

from app.shared.database import get_db
from app.dependencies import get_current_active_user, get_current_admin_user
from app.user_management.user_models import User
from app.user_management.user_service import hash_password, verify_password
from app.shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["user-management"])

# Pydantic models
class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: Optional[str] = None

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

class UserListResponse(BaseModel):
    users: List[UserProfile]
    total_count: int
    page: int
    page_size: int

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class UserStatsResponse(BaseModel):
    total_users: int
    active_users: int
    verified_users: int
    registrations_this_month: int
    last_login_stats: dict

class UserActivationRequest(BaseModel):
    is_active: bool
    reason: Optional[str] = None


@router.get("/profile", response_model=UserProfile,
           summary="Get current user profile",
           description="Retrieve current authenticated user's profile information")
async def get_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's profile"""
    try:
        logger.info("User profile retrieved", user_id=str(current_user.id))

        return UserProfile(
            id=str(current_user.id),
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name,
            phone=current_user.phone,
            is_active=current_user.is_active,
            is_verified=current_user.is_verified,
            created_at=current_user.created_at.isoformat() + "Z" if current_user.created_at else None,
            last_login=current_user.last_login.isoformat() + "Z" if current_user.last_login else None
        )

    except Exception as e:
        logger.error("Failed to get user profile",
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PROFILE_FETCH_FAILED",
                "message": "Failed to retrieve user profile"
            }
        )


@router.put("/profile", response_model=UserProfile,
           summary="Update user profile",
           description="Update current user's profile information")
async def update_user_profile(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    try:
        # Check if email is being changed and if it's already taken
        if update_data.email and update_data.email != current_user.email:
            existing_user = db.query(User).filter(
                User.email == update_data.email,
                User.id != current_user.id
            ).first()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "EMAIL_ALREADY_EXISTS",
                        "message": "Email address is already registered"
                    }
                )

        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(current_user, field, value)

        # If email was changed, mark as unverified
        if update_data.email and update_data.email != current_user.email:
            current_user.is_verified = False

        current_user.updated_at = datetime.utcnow()
        db.commit()

        logger.info("User profile updated",
                   user_id=str(current_user.id),
                   updated_fields=list(update_dict.keys()))

        return UserProfile(
            id=str(current_user.id),
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name,
            phone=current_user.phone,
            is_active=current_user.is_active,
            is_verified=current_user.is_verified,
            created_at=current_user.created_at.isoformat() + "Z" if current_user.created_at else None,
            last_login=current_user.last_login.isoformat() + "Z" if current_user.last_login else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update user profile",
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PROFILE_UPDATE_FAILED",
                "message": "Failed to update user profile"
            }
        )


@router.post("/change-password",
            summary="Change user password",
            description="Change current user's password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_CURRENT_PASSWORD",
                    "message": "Current password is incorrect"
                }
            )

        # Validate new password confirmation
        if password_data.new_password != password_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "PASSWORD_MISMATCH",
                    "message": "New password and confirmation do not match"
                }
            )

        # Validate password strength (basic)
        if len(password_data.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "WEAK_PASSWORD",
                    "message": "Password must be at least 8 characters long"
                }
            )

        # Update password
        current_user.password_hash = hash_password(password_data.new_password)
        current_user.updated_at = datetime.utcnow()
        db.commit()

        logger.info("User password changed", user_id=str(current_user.id))

        return {
            "message": "Password changed successfully",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to change password",
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PASSWORD_CHANGE_FAILED",
                "message": "Failed to change password"
            }
        )


@router.delete("/account",
              summary="Delete user account",
              description="Delete current user's account (soft delete)")
async def delete_user_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete user account (soft delete)"""
    try:
        # Soft delete - mark as inactive
        current_user.is_active = False
        current_user.updated_at = datetime.utcnow()
        db.commit()

        logger.info("User account deleted (soft delete)", user_id=str(current_user.id))

        return {
            "message": "Account deleted successfully",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        logger.error("Failed to delete user account",
                    user_id=str(current_user.id),
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ACCOUNT_DELETE_FAILED",
                "message": "Failed to delete account"
            }
        )


# Admin-only endpoints
@router.get("/", response_model=UserListResponse,
           summary="List all users (Admin only)",
           description="Retrieve paginated list of all users - admin access required")
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by username or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    try:
        # Build query
        query = db.query(User)

        # Apply filters
        if search:
            query = query.filter(
                (User.username.ilike(f"%{search}%")) |
                (User.email.ilike(f"%{search}%"))
            )

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        # Get total count
        total_count = query.count()

        # Apply pagination
        users = query.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size).all()

        # Build response
        user_profiles = []
        for user in users:
            profile = UserProfile(
                id=str(user.id),
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                phone=user.phone,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at.isoformat() + "Z" if user.created_at else None,
                last_login=user.last_login.isoformat() + "Z" if user.last_login else None
            )
            user_profiles.append(profile)

        logger.info("Users list retrieved",
                   admin_user_id=str(current_user.id),
                   total_count=total_count,
                   page=page)

        return UserListResponse(
            users=user_profiles,
            total_count=total_count,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error("Failed to list users",
                    admin_user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "USERS_LIST_FAILED",
                "message": "Failed to retrieve users list"
            }
        )


@router.get("/{user_id}", response_model=UserProfile,
           summary="Get user by ID (Admin only)",
           description="Retrieve specific user by ID - admin access required")
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "USER_NOT_FOUND",
                    "message": "User not found"
                }
            )

        logger.info("User retrieved by admin",
                   admin_user_id=str(current_user.id),
                   target_user_id=user_id)

        return UserProfile(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat() + "Z" if user.created_at else None,
            last_login=user.last_login.isoformat() + "Z" if user.last_login else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get user by ID",
                    admin_user_id=str(current_user.id),
                    target_user_id=user_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "USER_FETCH_FAILED",
                "message": "Failed to retrieve user"
            }
        )


@router.put("/{user_id}/activation",
           summary="Activate/deactivate user (Admin only)",
           description="Activate or deactivate user account - admin access required")
async def update_user_activation(
    user_id: str,
    activation_data: UserActivationRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user activation status (admin only)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "USER_NOT_FOUND",
                    "message": "User not found"
                }
            )

        # Prevent admin from deactivating themselves
        if user.id == current_user.id and not activation_data.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "SELF_DEACTIVATION_FORBIDDEN",
                    "message": "Cannot deactivate your own account"
                }
            )

        user.is_active = activation_data.is_active
        user.updated_at = datetime.utcnow()
        db.commit()

        action = "activated" if activation_data.is_active else "deactivated"
        logger.info(f"User {action} by admin",
                   admin_user_id=str(current_user.id),
                   target_user_id=user_id,
                   reason=activation_data.reason)

        return {
            "message": f"User {action} successfully",
            "user_id": user_id,
            "is_active": activation_data.is_active,
            "reason": activation_data.reason,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update user activation",
                    admin_user_id=str(current_user.id),
                    target_user_id=user_id,
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ACTIVATION_UPDATE_FAILED",
                "message": "Failed to update user activation status"
            }
        )


@router.get("/stats/overview", response_model=UserStatsResponse,
           summary="Get user statistics (Admin only)",
           description="Retrieve user statistics and metrics - admin access required")
async def get_user_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get user statistics (admin only)"""
    try:
        from sqlalchemy import func, extract

        # Total users
        total_users = db.query(User).count()

        # Active users
        active_users = db.query(User).filter(User.is_active == True).count()

        # Verified users
        verified_users = db.query(User).filter(User.is_verified == True).count()

        # Registrations this month
        current_month = datetime.utcnow().month
        current_year = datetime.utcnow().year
        registrations_this_month = db.query(User).filter(
            extract('month', User.created_at) == current_month,
            extract('year', User.created_at) == current_year
        ).count()

        # Last login stats
        users_with_login = db.query(User).filter(User.last_login.isnot(None)).count()
        never_logged_in = total_users - users_with_login

        last_login_stats = {
            "users_with_login": users_with_login,
            "never_logged_in": never_logged_in,
            "login_rate": round((users_with_login / total_users * 100), 2) if total_users > 0 else 0
        }

        logger.info("User statistics retrieved", admin_user_id=str(current_user.id))

        return UserStatsResponse(
            total_users=total_users,
            active_users=active_users,
            verified_users=verified_users,
            registrations_this_month=registrations_this_month,
            last_login_stats=last_login_stats
        )

    except Exception as e:
        logger.error("Failed to get user statistics",
                    admin_user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "STATS_FETCH_FAILED",
                "message": "Failed to retrieve user statistics"
            }
        )