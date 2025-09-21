# 🧪 Module 1 Testing Guide

This guide provides instructions for manually testing Module 1 (User Management & Authentication) functionality.

## 📋 Quick Start

### Option 1: Comprehensive Test Runner (Recommended)
```bash
# Run from project root directory
python run_module1_tests.py
```

### Option 2: Quick Test Script
```bash
# Run from project root directory
./quick_test_module1.sh
```

### Option 3: Individual Test Commands
```bash
# Unit tests only
source .venv/bin/activate
python -m pytest tests/module1_user_auth/test_user_service.py -v

# Manual validation only
source .venv/bin/activate
python tests/module1_user_auth/manual_test_validation.py

# API tests only (simplified)
source .venv/bin/activate
cd tests/module1_user_auth
python -m pytest test_auth_api_simple.py -v
```

## 🔧 Prerequisites

1. **Correct Directory**: Must be in the AI-social project root
2. **Virtual Environment**: `.venv` directory must exist
3. **Dependencies**: Run `pip install -r requirements.txt` in virtual environment

## 📊 What Gets Tested

### 🔐 Unit Tests (26 tests)
- **Password Operations**: Hashing, verification, salt validation
- **JWT Tokens**: Creation, verification, expiration, invalid formats
- **User Creation**: Valid data, duplicates, constraints
- **Authentication**: Login, logout, invalid credentials
- **User Lookup**: By ID, by username, not found scenarios
- **Password Updates**: Current password verification, new password
- **Profile Updates**: Name, email, duplicate email prevention

### 🌐 API Integration Tests (9 tests)
- **POST /auth/register**: User registration with validation
- **POST /auth/login**: Login with username or email
- **GET /auth/me**: Protected endpoint access
- **PUT /auth/password**: Password change functionality
- **POST /auth/logout**: Session termination
- **POST /auth/refresh**: Token refresh
- **Error Scenarios**: 401, 409, 422 responses

### ✅ Manual Validation Tests (3 tests)
- **Password Security**: Direct bcrypt operations
- **JWT Functionality**: Token lifecycle management
- **Schema Validation**: Pydantic model validation

### 🔧 Component Tests (3 tests)
- **Individual Service Methods**: Isolated functionality testing
- **Error Handling**: Exception and edge case testing
- **Integration Points**: Service layer interactions

## 📈 Expected Results

### ✅ Success Criteria
- **Unit Tests**: 26/26 passing (100%)
- **API Tests**: 5-9/9 passing (55-100%)
- **Manual Validation**: 3/3 passing (100%)
- **Component Tests**: 3/3 passing (100%)

### 🎯 Overall Success Rate
- **Excellent**: ≥90% (Ready for production)
- **Good**: 70-89% (Minor issues to address)
- **Needs Work**: <70% (Significant issues)

## 🐛 Common Issues & Solutions

### Issue: Import Errors
```bash
# Solution: Ensure virtual environment is activated
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: Database Errors
```bash
# Solution: Clean test databases
rm -f test*.db
```

### Issue: JWT Secret Key Error
```bash
# Solution: Set environment variables
export JWT_SECRET_KEY="test-secret-key"
export JWT_ALGORITHM="HS256"
```

### Issue: Permission Denied
```bash
# Solution: Make scripts executable
chmod +x run_module1_tests.py
chmod +x quick_test_module1.sh
```

## 📝 Test Output Examples

### Successful Run
```
🎉 MODULE 1 IS WORKING EXCELLENTLY!
✅ Ready for production use

📊 Overall Results:
   Total Tests: 35
   Passed: 32
   Failed: 3
   Success Rate: 91.4%
```

### Test Report
Each comprehensive test run generates a JSON report:
```
module1_test_report_20250921_HHMMSS.json
```

## 🔍 Debugging Failed Tests

### Check Individual Components
```bash
# Test password operations only
source .venv/bin/activate
python -c "
from app.user_management.user_service import UserService
import os
os.environ['JWT_SECRET_KEY']='test'
pwd='test123'
hashed=UserService.hash_password(pwd)
print('Password test:', UserService.verify_password(pwd, hashed))
"
```

### Check JWT Operations
```bash
# Test JWT functionality only
source .venv/bin/activate
python -c "
from app.user_management.user_service import UserService
import os
os.environ['JWT_SECRET_KEY']='test'
os.environ['JWT_ALGORITHM']='HS256'
token=UserService.create_access_token({'sub': 'test', 'user_id': '123'})
data=UserService.verify_token(token)
print('JWT test:', data.username == 'test')
"
```

### Check Database Connection
```bash
# Test database operations
source .venv/bin/activate
python -c "
from app.shared.database import engine
print('Database connection:', engine.connect())
"
```

## 📞 Support

If tests fail consistently:

1. **Check Environment**: Ensure all prerequisites are met
2. **Check Dependencies**: Verify all packages are installed
3. **Check Configuration**: Validate environment variables
4. **Review Logs**: Check test output for specific error messages
5. **Clean State**: Remove test databases and try again

## 🚀 Next Steps

After Module 1 tests pass successfully:

1. **Review Results**: Check the generated test report
2. **Address Issues**: Fix any failing tests if needed
3. **Proceed to Module 2**: Begin Application Management testing
4. **Document Changes**: Update PROJECT_STATUS.md with results

---

**📋 Test Commands Summary:**
- **Comprehensive**: `python run_module1_tests.py`
- **Quick**: `./quick_test_module1.sh`
- **Unit Only**: `python -m pytest tests/module1_user_auth/test_user_service.py -v`
- **Manual Only**: `python tests/module1_user_auth/manual_test_validation.py`