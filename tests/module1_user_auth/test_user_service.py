"""
Unit tests for UserService class

Tests cover:
- User creation and validation
- Password hashing and verification
- JWT token creation and validation
- User authentication
- Profile updates
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.user_management.user_service import UserService
from app.user_management.user_models import User
from app.user_management.auth_schemas import UserCreate, UserLogin, TokenData
from app.shared.exceptions import (
    AuthenticationError,
    DuplicateUserError,
    UserNotFoundError,
    ValidationError
)


class TestPasswordOperations:
    """Test password hashing and verification"""

    def test_hash_password_creates_hash(self):
        """Test that password hashing creates a valid hash"""
        password = "testpassword123"
        hashed = UserService.hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 20  # Bcrypt hashes are typically 60 chars

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "testpassword123"
        hashed = UserService.hash_password(password)

        assert UserService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = UserService.hash_password(password)

        assert UserService.verify_password(wrong_password, hashed) is False

    def test_hash_password_different_results(self):
        """Test that same password produces different hashes (salt)"""
        password = "testpassword123"
        hash1 = UserService.hash_password(password)
        hash2 = UserService.hash_password(password)

        assert hash1 != hash2
        # But both should verify correctly
        assert UserService.verify_password(password, hash1) is True
        assert UserService.verify_password(password, hash2) is True


class TestJWTTokenOperations:
    """Test JWT token creation and verification"""

    def test_create_access_token_default_expiry(self):
        """Test JWT token creation with default expiry"""
        data = {"sub": "testuser", "user_id": "123"}
        token = UserService.create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long

    def test_create_access_token_custom_expiry(self):
        """Test JWT token creation with custom expiry"""
        data = {"sub": "testuser", "user_id": "123"}
        expires_delta = timedelta(hours=1)
        token = UserService.create_access_token(data, expires_delta)

        assert token is not None
        assert isinstance(token, str)

    def test_verify_token_valid(self):
        """Test JWT token verification with valid token"""
        data = {"sub": "testuser", "user_id": "123"}
        token = UserService.create_access_token(data)

        token_data = UserService.verify_token(token)

        assert token_data.username == "testuser"
        assert token_data.user_id == "123"

    def test_verify_token_invalid_format(self):
        """Test JWT token verification with invalid token format"""
        invalid_token = "invalid.token.here"

        with pytest.raises(AuthenticationError) as exc_info:
            UserService.verify_token(invalid_token)

        assert exc_info.value.error_code == "TOKEN_INVALID"

    def test_verify_token_expired(self):
        """Test JWT token verification with expired token"""
        data = {"sub": "testuser", "user_id": "123"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = UserService.create_access_token(data, expires_delta)

        with pytest.raises(AuthenticationError) as exc_info:
            UserService.verify_token(token)

        assert exc_info.value.error_code == "TOKEN_INVALID"

    def test_verify_token_missing_data(self):
        """Test JWT token verification with missing required data"""
        # Create token without required fields
        data = {"sub": "testuser"}  # Missing user_id
        token = UserService.create_access_token(data)

        with pytest.raises(AuthenticationError) as exc_info:
            UserService.verify_token(token)

        assert exc_info.value.error_code == "INVALID_TOKEN"


class TestUserCreation:
    """Test user creation functionality"""

    def test_create_user_success(self):
        """Test successful user creation"""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )

        # Mock the created user
        mock_user = User(
            id="user-123",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User"
        )
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch.object(UserService, 'hash_password', return_value="hashed_password"):
            with patch('app.user_management.user_service.User', return_value=mock_user):
                result = UserService.create_user(mock_db, user_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result == mock_user

    def test_create_user_duplicate_username(self):
        """Test user creation with duplicate username"""
        mock_db = Mock(spec=Session)
        existing_user = User(username="testuser", email="other@example.com")
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )

        with pytest.raises(DuplicateUserError) as exc_info:
            UserService.create_user(mock_db, user_data)

        assert exc_info.value.error_code == "USERNAME_EXISTS"
        assert "Username already exists" in exc_info.value.message

    def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email"""
        mock_db = Mock(spec=Session)
        existing_user = User(username="otheruser", email="test@example.com")
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )

        with pytest.raises(DuplicateUserError) as exc_info:
            UserService.create_user(mock_db, user_data)

        assert exc_info.value.error_code == "EMAIL_EXISTS"
        assert "Email already exists" in exc_info.value.message


class TestUserAuthentication:
    """Test user authentication functionality"""

    def test_authenticate_user_success(self):
        """Test successful user authentication"""
        mock_db = Mock(spec=Session)

        # Create mock user
        mock_user = User(
            id="user-123",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            is_active=True
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.commit.return_value = None

        login_data = UserLogin(username="testuser", password="password123")

        with patch.object(UserService, 'verify_password', return_value=True):
            result = UserService.authenticate_user(mock_db, login_data)

        assert result == mock_user
        assert isinstance(mock_user.last_login, datetime)
        mock_db.commit.assert_called_once()

    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        login_data = UserLogin(username="nonexistent", password="password123")

        with pytest.raises(AuthenticationError) as exc_info:
            UserService.authenticate_user(mock_db, login_data)

        assert exc_info.value.error_code == "INVALID_CREDENTIALS"

    def test_authenticate_user_inactive(self):
        """Test authentication with inactive user"""
        mock_db = Mock(spec=Session)

        # Create inactive user
        mock_user = User(
            id="user-123",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            is_active=False
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        login_data = UserLogin(username="testuser", password="password123")

        with pytest.raises(AuthenticationError) as exc_info:
            UserService.authenticate_user(mock_db, login_data)

        assert exc_info.value.error_code == "ACCOUNT_INACTIVE"

    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        mock_db = Mock(spec=Session)

        mock_user = User(
            id="user-123",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            is_active=True
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        login_data = UserLogin(username="testuser", password="wrongpassword")

        with patch.object(UserService, 'verify_password', return_value=False):
            with pytest.raises(AuthenticationError) as exc_info:
                UserService.authenticate_user(mock_db, login_data)

        assert exc_info.value.error_code == "INVALID_CREDENTIALS"


class TestUserLookup:
    """Test user lookup functionality"""

    def test_get_user_by_id_success(self):
        """Test successful user lookup by ID"""
        mock_db = Mock(spec=Session)

        mock_user = User(id="user-123", username="testuser")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = UserService.get_user_by_id(mock_db, "user-123")

        assert result == mock_user

    def test_get_user_by_id_not_found(self):
        """Test user lookup by ID when user doesn't exist"""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(UserNotFoundError) as exc_info:
            UserService.get_user_by_id(mock_db, "nonexistent-id")

        assert exc_info.value.error_code == "USER_NOT_FOUND"

    def test_get_user_by_username_success(self):
        """Test successful user lookup by username"""
        mock_db = Mock(spec=Session)

        mock_user = User(id="user-123", username="testuser")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = UserService.get_user_by_username(mock_db, "testuser")

        assert result == mock_user

    def test_get_user_by_username_not_found(self):
        """Test user lookup by username when user doesn't exist"""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(UserNotFoundError) as exc_info:
            UserService.get_user_by_username(mock_db, "nonexistentuser")

        assert exc_info.value.error_code == "USER_NOT_FOUND"


class TestPasswordUpdate:
    """Test password update functionality"""

    def test_update_user_password_success(self):
        """Test successful password update"""
        mock_db = Mock(spec=Session)

        mock_user = User(
            id="user-123",
            password_hash="old_hashed_password"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch.object(UserService, 'verify_password', return_value=True):
            with patch.object(UserService, 'hash_password', return_value="new_hashed_password"):
                result = UserService.update_user_password(
                    mock_db, "user-123", "oldpassword", "newpassword"
                )

        assert result == mock_user
        assert mock_user.password_hash == "new_hashed_password"
        mock_db.commit.assert_called_once()

    def test_update_user_password_wrong_current(self):
        """Test password update with wrong current password"""
        mock_db = Mock(spec=Session)

        mock_user = User(
            id="user-123",
            password_hash="old_hashed_password"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch.object(UserService, 'verify_password', return_value=False):
            with pytest.raises(AuthenticationError) as exc_info:
                UserService.update_user_password(
                    mock_db, "user-123", "wrongoldpassword", "newpassword"
                )

        assert exc_info.value.error_code == "INVALID_PASSWORD"


class TestProfileUpdate:
    """Test user profile update functionality"""

    def test_update_user_profile_full_name(self):
        """Test updating user full name"""
        mock_db = Mock(spec=Session)

        mock_user = User(
            id="user-123",
            full_name="Old Name",
            email="test@example.com"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = UserService.update_user_profile(
            mock_db, "user-123", full_name="New Name"
        )

        assert result == mock_user
        assert mock_user.full_name == "New Name"
        mock_db.commit.assert_called_once()

    def test_update_user_profile_email(self):
        """Test updating user email"""
        mock_db = Mock(spec=Session)

        mock_user = User(
            id="user-123",
            full_name="Test User",
            email="old@example.com"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        # Mock check for existing email
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_user, None]
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = UserService.update_user_profile(
            mock_db, "user-123", email="new@example.com"
        )

        assert result == mock_user
        assert mock_user.email == "new@example.com"
        mock_db.commit.assert_called_once()

    def test_update_user_profile_duplicate_email(self):
        """Test updating user email to existing email"""
        mock_db = Mock(spec=Session)

        mock_user = User(id="user-123", email="old@example.com")
        existing_user = User(id="other-user", email="new@example.com")

        # First call returns current user, second call returns existing user with new email
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_user, existing_user]

        with pytest.raises(DuplicateUserError) as exc_info:
            UserService.update_user_profile(
                mock_db, "user-123", email="new@example.com"
            )

        assert exc_info.value.error_code == "EMAIL_EXISTS"