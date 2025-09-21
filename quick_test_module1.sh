#!/bin/bash
# Quick Test Script for Module 1 - User Management & Authentication
# Usage: ./quick_test_module1.sh

echo "🧪 Module 1 - Quick Test Runner"
echo "================================"

# Check if we're in the right directory
if [ ! -f "app/user_management/user_service.py" ]; then
    echo "❌ Error: Not in the correct project directory"
    echo "Please run this script from the AI-social project root"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "Please create a virtual environment: python -m venv .venv"
    exit 1
fi

echo "✅ Environment check passed"
echo ""

# Set test environment variables
export ENVIRONMENT="testing"
export DATABASE_URL="sqlite:///./test_quick.db"
export JWT_SECRET_KEY="test-secret-key-for-quick-test"
export JWT_ALGORITHM="HS256"
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES="60"

echo "🔄 Running Unit Tests..."
echo "------------------------"
source .venv/bin/activate && python -m pytest tests/module1_user_auth/test_user_service.py --tb=short -q

echo ""
echo "🔄 Running Manual Validation..."
echo "-------------------------------"
source .venv/bin/activate && python tests/module1_user_auth/manual_test_validation.py

echo ""
echo "🔄 Quick Component Tests..."
echo "---------------------------"

# Test password operations
echo -n "Password Operations: "
source .venv/bin/activate && python -c "
from app.user_management.user_service import UserService
import os
os.environ['JWT_SECRET_KEY']='test'
pwd='test123'
hashed=UserService.hash_password(pwd)
result = UserService.verify_password(pwd, hashed)
print('✅ PASS' if result else '❌ FAIL')
" 2>/dev/null

# Test JWT operations
echo -n "JWT Operations: "
source .venv/bin/activate && python -c "
from app.user_management.user_service import UserService
import os
os.environ['JWT_SECRET_KEY']='test'
os.environ['JWT_ALGORITHM']='HS256'
try:
    token=UserService.create_access_token({'sub': 'test', 'user_id': '123'})
    data=UserService.verify_token(token)
    print('✅ PASS' if data.username=='test' else '❌ FAIL')
except Exception as e:
    print('❌ FAIL')
" 2>/dev/null

# Test schema validation
echo -n "Schema Validation: "
source .venv/bin/activate && python -c "
from app.user_management.auth_schemas import UserCreate
try:
    user=UserCreate(username='test', email='test@example.com', password='pass')
    print('✅ PASS' if user.username=='test' else '❌ FAIL')
except Exception as e:
    print('❌ FAIL')
" 2>/dev/null

echo ""
echo "🎯 Quick Test Complete!"
echo "For comprehensive testing, run: python run_module1_tests.py"