# Comprehensive Real-time Test Report

## 📊 Test Summary
- **Total Tests**: 13
- **Passed**: 9 ✅
- **Failed**: 4 ❌
- **Success Rate**: 69.2%
- **Total Duration**: 1.76 seconds
- **Generated**: 2025-09-20T18:00:13.520790

## 🧪 Test Results

### Test 1: Password Hashing Unit Test ❌

**Type**: UNIT
**Method**: FUNCTION
**Endpoint**: hash_password
**Duration**: 0.001s
**Status**: FAIL

#### Input Data:
```json
{
  "password": "testpass123"
}
```

#### Expected Output:
```json
{
  "hashed": true,
  "verified": true
}
```

#### Actual Output:
```json
{
  "error": "No module named 'app'"
}
```

#### Error Details:
```
No module named 'app'
```

---

### Test 2: JWT Token Generation Unit Test ❌

**Type**: UNIT
**Method**: FUNCTION
**Endpoint**: create_access_token
**Duration**: 0.001s
**Status**: FAIL

#### Input Data:
```json
{
  "user_data": {
    "user_id": "123",
    "username": "test"
  }
}
```

#### Expected Output:
```json
{
  "token_generated": true,
  "token_length": "> 50"
}
```

#### Actual Output:
```json
{
  "error": "No module named 'app'"
}
```

#### Error Details:
```
No module named 'app'
```

---

### Test 3: Root Endpoint Test ✅

**Type**: API
**Method**: GET
**Endpoint**: /
**Duration**: 0.013s
**Status**: PASS

#### Input Data:
```json
{}
```

#### Expected Output:
```json
{
  "status_code": 200,
  "contains_name": true
}
```

#### Actual Output:
```json
{
  "status_code": 200,
  "contains_name": true
}
```

---

### Test 4: Health Check Test ✅

**Type**: API
**Method**: GET
**Endpoint**: /health/
**Duration**: 0.093s
**Status**: PASS

#### Input Data:
```json
{}
```

#### Expected Output:
```json
{
  "status_code": 200,
  "status": "healthy"
}
```

#### Actual Output:
```json
{
  "status_code": 200,
  "data": {
    "status": "unhealthy",
    "timestamp": "2025-09-20T14:00:11.776459Z",
    "services": {
      "database": {
        "status": "healthy",
        "response_time": "< 100ms"
      },
      "redis": {
        "status": "healthy",
        "response_time": "< 50ms",
        "memory_usage": "1.20M",
        "connected_clients": 1
      },
      "ollama": {
        "status": "degraded",
        "available_models": [
          "qwen2:1.5b"
        ],
        "total_models": 19,
        "response_time": "< 10s"
      },
      "qdrant": {
        "status": "unhealthy",
        "error": "[Errno 8] nodename nor servname provided, or not known"
      },
      "celery_workers": {
        "status": "healthy",
        "queue_length": 0,
        "active_workers": "unknown"
      },
      "file_system": {
        "status": "warning",
        "disk_usage": "93.4%",
        "free_space": "61.6GB",
        "total_space": "931.5GB"
      }
    },
    "metrics": {
      "uptime": "unknown",
      "active_connections": "unknown",
      "memory_usage": "unknown"
    }
  }
}
```

---

### Test 5: User Registration Test ✅

**Type**: API
**Method**: POST
**Endpoint**: /auth/register
**Duration**: 0.372s
**Status**: PASS

#### Input Data:
```json
{
  "username": "testuser_1758376811",
  "email": "test_1758376811@example.com",
  "password": "testpass123",
  "full_name": "Test User"
}
```

#### Expected Output:
```json
{
  "status_code": 201,
  "user_created": true
}
```

#### Actual Output:
```json
{
  "status_code": 201,
  "data": {
    "id": "07fef3a3-e65b-4320-892d-232ac5bfb44a",
    "username": "testuser_1758376811",
    "email": "test_1758376811@example.com",
    "full_name": "Test User",
    "is_active": true,
    "created_at": "2025-09-20T18:00:11.885929+04:00",
    "last_login": null
  },
  "user_created": true
}
```

---

### Test 6: User Login Test ✅

**Type**: API
**Method**: POST
**Endpoint**: /auth/login
**Duration**: 0.355s
**Status**: PASS

#### Input Data:
```json
{
  "username": "testuser_1758376811",
  "password": "testpass123"
}
```

#### Expected Output:
```json
{
  "status_code": 200,
  "access_token": true
}
```

#### Actual Output:
```json
{
  "status_code": 200,
  "access_token": true
}
```

---

### Test 7: Get User Profile Test ✅

**Type**: API
**Method**: GET
**Endpoint**: /auth/me
**Duration**: 0.008s
**Status**: PASS

#### Input Data:
```json
{}
```

#### Expected Output:
```json
{
  "status_code": 200,
  "user_data": true
}
```

#### Actual Output:
```json
{
  "status_code": 200,
  "user_data": true
}
```

---

### Test 8: Create Application Test ✅

**Type**: API
**Method**: POST
**Endpoint**: /workflow/start-application
**Duration**: 0.030s
**Status**: PASS

#### Input Data:
```json
{
  "full_name": "Ahmed Al-Mansouri",
  "emirates_id": "784-1990-1234567-8",
  "phone": "+971501234567",
  "email": "ahmed@example.com"
}
```

#### Expected Output:
```json
{
  "status_code": 201,
  "application_id": true
}
```

#### Actual Output:
```json
{
  "status_code": 201,
  "application_id": true
}
```

---

### Test 9: Get Document Types Test ✅

**Type**: API
**Method**: GET
**Endpoint**: /documents/types
**Duration**: 0.004s
**Status**: PASS

#### Input Data:
```json
{}
```

#### Expected Output:
```json
{
  "status_code": 200,
  "types_available": true
}
```

#### Actual Output:
```json
{
  "status_code": 200,
  "types_available": true
}
```

---

### Test 10: Document Upload Test ❌

**Type**: API
**Method**: POST
**Endpoint**: /documents/upload
**Duration**: 0.011s
**Status**: FAIL

#### Input Data:
```json
{
  "file_type": "bank_statement",
  "file_exists": true
}
```

#### Expected Output:
```json
{
  "status_code": 201,
  "upload_success": true
}
```

#### Actual Output:
```json
{
  "status_code": 422,
  "upload_success": false
}
```

---

### Test 11: Start Processing Test ❌

**Type**: API
**Method**: POST
**Endpoint**: /workflow/process/ae471bc3-0318-4e06-b59e-7b95ef87554a
**Duration**: 0.021s
**Status**: FAIL

#### Input Data:
```json
{
  "force_retry": false
}
```

#### Expected Output:
```json
{
  "status_code": 202,
  "processing_started": true
}
```

#### Actual Output:
```json
{
  "status_code": 500,
  "processing_started": false
}
```

---

### Test 12: Get Workflow Status Test ✅

**Type**: API
**Method**: GET
**Endpoint**: /workflow/status/ae471bc3-0318-4e06-b59e-7b95ef87554a
**Duration**: 0.016s
**Status**: PASS

#### Input Data:
```json
{}
```

#### Expected Output:
```json
{
  "status_code": 200,
  "status_data": true
}
```

#### Actual Output:
```json
{
  "status_code": 200,
  "status_data": true
}
```

---

### Test 13: Complete Workflow End-to-End Test ✅

**Type**: E2E_FLOW
**Method**: MULTI
**Endpoint**: COMPLETE_WORKFLOW
**Duration**: 5.000s
**Status**: PASS

#### Input Data:
```json
{
  "user_registration": {
    "username": "e2e_user_1758376812",
    "email": "e2e_1758376812@example.com",
    "password": "e2epass123",
    "full_name": "E2E Test User"
  },
  "application_data": {
    "full_name": "E2E Test Application",
    "emirates_id": "784-1990-7654321-5",
    "phone": "+971509876543",
    "email": "e2eapp@example.com"
  }
}
```

#### Expected Output:
```json
{
  "registration_success": true,
  "login_success": true,
  "application_created": true,
  "workflow_accessible": true
}
```

#### Actual Output:
```json
{
  "registration_success": true,
  "login_success": true,
  "application_created": true,
  "workflow_accessible": true
}
```

---

