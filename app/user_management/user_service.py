"""
User management business logic
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.config import settings
from app.user_management.user_models import User
from app.user_management.auth_schemas import UserCreate, UserLogin, TokenData
from app.shared.exceptions import (
    AuthenticationError,
    DuplicateUserError,
    UserNotFoundError,
    ValidationError
)
from app.shared.logging_config import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Service class for user management operations"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> TokenData:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            username: str = payload.get("sub")
            user_id: str = payload.get("user_id")

            if username is None or user_id is None:
                raise AuthenticationError("Invalid token format", "INVALID_TOKEN")

            return TokenData(username=username, user_id=user_id)
        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            raise AuthenticationError("Invalid or expired token", "TOKEN_INVALID")

    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.username == user_data.username) | (User.email == user_data.email)
            ).first()

            if existing_user:
                if existing_user.username == user_data.username:
                    raise DuplicateUserError("Username already exists", "USERNAME_EXISTS")
                else:
                    raise DuplicateUserError("Email already exists", "EMAIL_EXISTS")

            # Create new user
            hashed_password = UserService.hash_password(user_data.password)
            db_user = User(
                username=user_data.username,
                email=user_data.email,
                password_hash=hashed_password,
                full_name=user_data.full_name
            )

            db.add(db_user)
            db.commit()
            db.refresh(db_user)

            logger.info("User created successfully",
                       user_id=str(db_user.id),
                       username=db_user.username)

            return db_user

        except IntegrityError as e:
            db.rollback()
            logger.error("Database integrity error during user creation", error=str(e))
            raise DuplicateUserError("User already exists", "USER_EXISTS")

    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> User:
        """Authenticate a user with username/email and password"""
        # Try to find user by username or email
        user = db.query(User).filter(
            (User.username == login_data.username) | (User.email == login_data.username)
        ).first()

        if not user:
            logger.warning("Login attempt with non-existent user", username=login_data.username)
            raise AuthenticationError("Invalid credentials", "INVALID_CREDENTIALS")

        if not user.is_active:
            logger.warning("Login attempt with inactive user", user_id=str(user.id))
            raise AuthenticationError("Account is deactivated", "ACCOUNT_INACTIVE")

        if not UserService.verify_password(login_data.password, user.password_hash):
            logger.warning("Invalid password attempt", user_id=str(user.id))
            raise AuthenticationError("Invalid credentials", "INVALID_CREDENTIALS")

        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()

        logger.info("User authenticated successfully", user_id=str(user.id))
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> User:
        """Get user by ID"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found", "USER_NOT_FOUND")
        return user

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User:
        """Get user by username"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise UserNotFoundError(f"User '{username}' not found", "USER_NOT_FOUND")
        return user

    @staticmethod
    def update_user_password(db: Session, user_id: str, current_password: str, new_password: str) -> User:
        """Update user password"""
        user = UserService.get_user_by_id(db, user_id)

        if not UserService.verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect", "INVALID_PASSWORD")

        user.password_hash = UserService.hash_password(new_password)
        db.commit()
        db.refresh(user)

        logger.info("Password updated successfully", user_id=str(user.id))
        return user

    @staticmethod
    def update_user_profile(db: Session, user_id: str, full_name: Optional[str] = None,
                          email: Optional[str] = None) -> User:
        """Update user profile information"""
        user = UserService.get_user_by_id(db, user_id)

        if email and email != user.email:
            # Check if email is already taken
            existing_user = db.query(User).filter(User.email == email, User.id != user_id).first()
            if existing_user:
                raise DuplicateUserError("Email already exists", "EMAIL_EXISTS")
            user.email = email

        if full_name is not None:
            user.full_name = full_name

        db.commit()
        db.refresh(user)

        logger.info("User profile updated", user_id=str(user.id))
        return user


# Standalone function aliases for convenience
hash_password = UserService.hash_password
verify_password = UserService.verify_password