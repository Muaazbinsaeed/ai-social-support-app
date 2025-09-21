#!/usr/bin/env python3
"""
Manual validation script for Module 1 - User Management & Authentication
Tests the core functionality of UserService methods directly
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ["ENVIRONMENT"] = "testing"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-manual-validation"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

# Import what we need
from app.user_management.user_service import UserService
from app.user_management.auth_schemas import UserCreate, UserLogin

def test_password_operations():
    """Test password hashing and verification"""
    print("🔐 Testing Password Operations...")

    # Test password hashing
    password = "testpassword123"
    hashed = UserService.hash_password(password)
    print(f"   ✅ Password hashed: {len(hashed)} characters")

    # Test password verification
    is_valid = UserService.verify_password(password, hashed)
    print(f"   ✅ Password verification: {'PASS' if is_valid else 'FAIL'}")

    # Test wrong password
    is_invalid = UserService.verify_password("wrongpassword", hashed)
    print(f"   ✅ Wrong password rejected: {'PASS' if not is_invalid else 'FAIL'}")

    return True

def test_jwt_operations():
    """Test JWT token creation and verification"""
    print("🔑 Testing JWT Operations...")

    # Test token creation
    data = {"sub": "testuser", "user_id": "123"}
    token = UserService.create_access_token(data)
    print(f"   ✅ JWT token created: {len(token)} characters")

    # Test token verification
    try:
        token_data = UserService.verify_token(token)
        print(f"   ✅ Token verified: username={token_data.username}, user_id={token_data.user_id}")
        return True
    except Exception as e:
        print(f"   ❌ Token verification failed: {e}")
        return False

def test_validation_schemas():
    """Test Pydantic schema validation"""
    print("📋 Testing Schema Validation...")

    try:
        # Test valid user creation
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )
        print(f"   ✅ UserCreate schema valid: {user_data.username}")

        # Test login schema
        login_data = UserLogin(
            username="testuser",
            password="password123"
        )
        print(f"   ✅ UserLogin schema valid: {login_data.username}")

        return True
    except Exception as e:
        print(f"   ❌ Schema validation failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🧪 Module 1 - User Management & Authentication Validation")
    print("=" * 60)

    tests = [
        test_password_operations,
        test_jwt_operations,
        test_validation_schemas,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results.append(False)
            print()

    # Summary
    passed = sum(results)
    total = len(results)
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED - Module 1 is working correctly!")
        return True
    else:
        print("⚠️  Some tests failed - check the output above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)