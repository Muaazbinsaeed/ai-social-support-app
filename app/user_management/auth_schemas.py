"""
Pydantic schemas for authentication and user management
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import re
from uuid import UUID


class UserCreate(BaseModel):
    """Schema for user registration"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username is required')
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Username must be between 3 and 50 characters')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not v:
            raise ValueError('Password is required')
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        if len(v) > 128:
            raise ValueError('Password must be less than 128 characters')
        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not v or not v.strip():
            raise ValueError('Email is required')
        return v.strip().lower()

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            if len(v) > 100:
                raise ValueError('Full name must be less than 100 characters')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str  # Can be username or email
    password: str

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username or email is required')
        return v.strip()

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not v:
            raise ValueError('Password is required')
        return v


class UserResponse(BaseModel):
    """Schema for user information in responses"""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: UserResponse


class TokenData(BaseModel):
    """Schema for token payload data"""
    username: Optional[str] = None
    user_id: Optional[str] = None


class PasswordUpdate(BaseModel):
    """Schema for password update"""
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError('New password must be at least 6 characters long')
        return v


class UserUpdate(BaseModel):
    """Schema for user profile update"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Full name cannot be empty')
        return v.strip() if v else None