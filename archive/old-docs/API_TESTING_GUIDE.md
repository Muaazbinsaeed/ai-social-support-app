# AI Social Security System - API Testing Guide

## 📋 Complete API Reference

### **Authentication APIs**

#### 1. User Registration
- **Endpoint**: `POST /auth/register`
- **Description**: Register a new user
- **Request Body**:
```json
{
  "username": "muaaz_test",
  "email": "muaaz.test@example.com",
  "password": "SecurePass123",
  "full_name": "Muaaz Bin Saeed",
  "phone": "+971501234567",
  "emirates_id": "784-1995-1234567-8"
}
```
- **Response**: User object with ID and creation timestamp

#### 2. User Login
- **Endpoint**: `POST /auth/login`
- **Description**: Authenticate user and get access token
- **Request Body**:
```json
{
  "username": "muaaz_test",
  "password": "SecurePass123"
}
```
- **Response**: JWT access token and user info

#### 3. Get Current User
- **Endpoint**: `GET /auth/me`
- **Description**: Get current authenticated user info
- **Headers**: `Authorization: Bearer {token}`
- **Response**: Current user object

### **Workflow APIs**

#### 4. Start Application
- **Endpoint**: `POST /workflow/start-application`
- **Description**: Create new social security application
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**:
```json
{
  "full_name": "Muaaz Bin Saeed",
  "emirates_id": "784-1995-1234567-8",
  "phone": "+971501234567",
  "email": "muaaz.test@example.com"
}
```
- **Response**: Application ID and initial status

#### 5. Upload Documents
- **Endpoint**: `POST /workflow/upload-documents/{application_id}`
- **Description**: Upload Emirates ID and bank statement
- **Headers**: `Authorization: Bearer {token}`
- **Request**: Multipart form data
  - `emirates_id`: Image file (JPG/PNG)
  - `bank_statement`: PDF file
- **Response**: Document IDs and upload status

#### 6. Start Processing
- **Endpoint**: `POST /workflow/process/{application_id}`
- **Description**: Initiate AI processing workflow
- **Headers**: `Authorization: Bearer {token}`
- **Response**: Processing job ID and estimated completion time

#### 7. Check Status
- **Endpoint**: `GET /workflow/status/{application_id}`
- **Description**: Get current processing status
- **Headers**: `Authorization: Bearer {token}`
- **Response**: Detailed status with progress and steps

#### 8. Get Results
- **Endpoint**: `GET /workflow/results/{application_id}`
- **Description**: Get final decision results
- **Headers**: `Authorization: Bearer {token}`
- **Response**: Decision outcome, confidence, and reasoning

### **Document APIs**

#### 9. Process Document OCR
- **Endpoint**: `POST /documents/process-ocr/{document_id}`
- **Description**: Extract text from document using OCR
- **Headers**: `Authorization: Bearer {token}`
- **Response**: Extracted text and confidence score

#### 10. Analyze Document
- **Endpoint**: `POST /documents/analyze/{document_id}`
- **Description**: AI analysis of document content
- **Headers**: `Authorization: Bearer {token}`
- **Response**: Structured data extraction results

#### 11. Get Document Status
- **Endpoint**: `GET /documents/status/{document_id}`
- **Description**: Check document processing status
- **Headers**: `Authorization: Bearer {token}`
- **Response**: Processing status and progress

### **Decision APIs**

#### 12. Make Decision
- **Endpoint**: `POST /decisions/evaluate`
- **Description**: Make eligibility decision using AI
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**:
```json
{
  "application_id": "uuid",
  "applicant_data": {...},
  "extracted_data": {...}
}
```
- **Response**: Decision outcome and reasoning

#### 13. Get Decision
- **Endpoint**: `GET /decisions/{decision_id}`
- **Description**: Get decision details
- **Headers**: `Authorization: Bearer {token}`
- **Response**: Decision object with full reasoning

#### 14. Override Decision
- **Endpoint**: `POST /decisions/{decision_id}/override`
- **Description**: Manual override of AI decision
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**:
```json
{
  "new_outcome": "approved",
  "override_reason": "Manual review completed",
  "reviewer_notes": "Additional documentation provided"
}
```

### **Admin APIs**

#### 15. Get Statistics
- **Endpoint**: `GET /admin/statistics`
- **Description**: System-wide statistics
- **Headers**: `Authorization: Bearer {admin_token}`
- **Response**: Decision stats, processing metrics

#### 16. List Applications
- **Endpoint**: `GET /admin/applications`
- **Description**: List all applications with filters
- **Headers**: `Authorization: Bearer {admin_token}`
- **Query Parameters**: `status`, `limit`, `offset`

### **Health Check APIs**

#### 17. Health Check
- **Endpoint**: `GET /health`
- **Description**: Basic health check
- **Response**: Service status

#### 18. Database Health
- **Endpoint**: `GET /health/db`
- **Description**: Database connectivity check
- **Response**: Database status

#### 19. Redis Health
- **Endpoint**: `GET /health/redis`
- **Description**: Redis connectivity check
- **Response**: Redis status

#### 20. Worker Health
- **Endpoint**: `GET /health/workers`
- **Description**: Celery worker status
- **Response**: Worker availability and queue status

## 🧪 Comprehensive Test Cases

### **Test Case 1: Complete User Journey**

```bash
#!/bin/bash
# Test Case 1: End-to-End User Flow

echo "=== AI SOCIAL SECURITY SYSTEM - COMPLETE TEST ==="

# 1. Register User
echo "1. Registering new user..."
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user_'$(date +%s)'",
    "email": "test.'$(date +%s)'@example.com",
    "password": "SecurePass123",
    "full_name": "Test User",
    "phone": "+971501234567",
    "emirates_id": "784-1995-1234567-8"
  }')

USER_ID=$(echo $REGISTER_RESPONSE | jq -r '.id')
USERNAME=$(echo $REGISTER_RESPONSE | jq -r '.username')

echo "✅ User registered: $USERNAME"

# 2. Login User
echo "2. Logging in user..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "'$USERNAME'",
    "password": "SecurePass123"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
echo "✅ Login successful, token obtained"

# 3. Start Application
echo "3. Starting application..."
APP_RESPONSE=$(curl -s -X POST http://localhost:8000/workflow/start-application \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "emirates_id": "784-1995-1234567-8",
    "phone": "+971501234567",
    "email": "test@example.com"
  }')

APP_ID=$(echo $APP_RESPONSE | jq -r '.application_id')
echo "✅ Application created: $APP_ID"

# 4. Upload Documents
echo "4. Uploading documents..."
UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8000/workflow/upload-documents/$APP_ID \
  -H "Authorization: Bearer $TOKEN" \
  -F "bank_statement=@/Users/muaazbinsaeed/Documents/Bank Muaaz Alfalah Statement.pdf" \
  -F "emirates_id=@/Users/muaazbinsaeed/Documents/EmirateIDFront.jpg")

UPLOAD_STATUS=$(echo $UPLOAD_RESPONSE | jq -r '.status')
echo "✅ Documents uploaded: $UPLOAD_STATUS"

# 5. Start Processing
echo "5. Starting processing..."
PROCESS_RESPONSE=$(curl -s -X POST http://localhost:8000/workflow/process/$APP_ID \
  -H "Authorization: Bearer $TOKEN")

JOB_ID=$(echo $PROCESS_RESPONSE | jq -r '.processing_job_id')
echo "✅ Processing started: $JOB_ID"

# 6. Monitor Status
echo "6. Monitoring processing status..."
for i in {1..12}; do
  STATUS_RESPONSE=$(curl -s -X GET http://localhost:8000/workflow/status/$APP_ID \
    -H "Authorization: Bearer $TOKEN")

  CURRENT_STATE=$(echo $STATUS_RESPONSE | jq -r '.current_state')
  PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress')

  echo "   Status: $CURRENT_STATE ($PROGRESS%)"

  if [ "$CURRENT_STATE" = "completed" ] || [ "$CURRENT_STATE" = "failed" ]; then
    break
  fi

  sleep 10
done

# 7. Get Results
echo "7. Getting final results..."
RESULTS_RESPONSE=$(curl -s -X GET http://localhost:8000/workflow/results/$APP_ID \
  -H "Authorization: Bearer $TOKEN")

if [ "$?" -eq 0 ]; then
  DECISION=$(echo $RESULTS_RESPONSE | jq -r '.decision_outcome // "pending"')
  CONFIDENCE=$(echo $RESULTS_RESPONSE | jq -r '.confidence // "N/A"')
  echo "✅ Final Decision: $DECISION (Confidence: $CONFIDENCE)"
else
  echo "⏳ Results not ready yet"
fi

echo "=== TEST COMPLETED ==="
```

### **Test Case 2: API Validation Tests**

```bash
#!/bin/bash
# Test Case 2: API Validation and Error Handling

echo "=== API VALIDATION TESTS ==="

# Test invalid registration
echo "Testing invalid registration..."
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "email": "invalid"}' | jq

# Test unauthorized access
echo "Testing unauthorized access..."
curl -s -X GET http://localhost:8000/auth/me | jq

# Test invalid file upload
echo "Testing invalid file upload..."
curl -s -X POST http://localhost:8000/workflow/upload-documents/invalid-id \
  -H "Authorization: Bearer invalid-token" \
  -F "file=@/tmp/empty.txt" | jq

echo "=== VALIDATION TESTS COMPLETED ==="
```

### **Test Case 3: Performance Tests**

```bash
#!/bin/bash
# Test Case 3: Performance and Load Testing

echo "=== PERFORMANCE TESTS ==="

# Test API response times
echo "Testing API response times..."

time curl -s http://localhost:8000/health > /dev/null
time curl -s http://localhost:8000/docs > /dev/null

# Test concurrent requests
echo "Testing concurrent requests..."
for i in {1..5}; do
  curl -s http://localhost:8000/health &
done
wait

echo "=== PERFORMANCE TESTS COMPLETED ==="
```

### **Test Case 4: Document Processing Tests**

```bash
#!/bin/bash
# Test Case 4: Document Processing and OCR Tests

echo "=== DOCUMENT PROCESSING TESTS ==="

# Register and login for testing
USERNAME="doc_test_$(date +%s)"
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "'$USERNAME'",
    "email": "'$USERNAME'@example.com",
    "password": "SecurePass123",
    "full_name": "Doc Test User",
    "phone": "+971501234567",
    "emirates_id": "784-1995-1234567-8"
  }' > /dev/null

TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "'$USERNAME'", "password": "SecurePass123"}' | jq -r '.access_token')

# Test document upload validation
echo "Testing document upload validation..."

# Test with invalid file types
curl -s -X POST http://localhost:8000/workflow/upload-documents/test-id \
  -H "Authorization: Bearer $TOKEN" \
  -F "bank_statement=@/etc/hosts" \
  -F "emirates_id=@/etc/hosts" | jq

# Test with missing files
curl -s -X POST http://localhost:8000/workflow/upload-documents/test-id \
  -H "Authorization: Bearer $TOKEN" | jq

echo "=== DOCUMENT PROCESSING TESTS COMPLETED ==="
```

## 📊 Coverage Testing Script

```bash
#!/bin/bash
# Complete API Coverage Test

echo "=========================================="
echo "AI SOCIAL SECURITY SYSTEM - FULL API TEST"
echo "=========================================="

# Function to test endpoint
test_endpoint() {
  local method=$1
  local endpoint=$2
  local description=$3
  local headers=$4
  local data=$5

  echo "Testing: $description"
  echo "  $method $endpoint"

  if [ "$method" = "GET" ]; then
    response=$(curl -s -w "%{http_code}" $headers http://localhost:8000$endpoint)
  else
    response=$(curl -s -w "%{http_code}" -X $method $headers http://localhost:8000$endpoint $data)
  fi

  status_code="${response: -3}"
  body="${response%???}"

  if [ "$status_code" -ge 200 ] && [ "$status_code" -lt 400 ]; then
    echo "  ✅ SUCCESS ($status_code)"
  else
    echo "  ❌ FAILED ($status_code)"
    echo "  Response: $body" | head -c 200
  fi
  echo ""
}

# Health checks
test_endpoint "GET" "/health" "Basic health check" "" ""
test_endpoint "GET" "/health/db" "Database health check" "" ""
test_endpoint "GET" "/health/redis" "Redis health check" "" ""

# Authentication tests (without valid data)
test_endpoint "POST" "/auth/register" "User registration (validation test)" "-H 'Content-Type: application/json'" "-d '{\"username\":\"test\"}'"
test_endpoint "POST" "/auth/login" "User login (validation test)" "-H 'Content-Type: application/json'" "-d '{\"username\":\"test\"}'"
test_endpoint "GET" "/auth/me" "Get current user (unauthorized)" "" ""

# Workflow tests (unauthorized)
test_endpoint "POST" "/workflow/start-application" "Start application (unauthorized)" "-H 'Content-Type: application/json'" "-d '{}'"
test_endpoint "GET" "/workflow/status/test-id" "Get status (unauthorized)" "" ""
test_endpoint "GET" "/workflow/results/test-id" "Get results (unauthorized)" "" ""

echo "=========================================="
echo "API COVERAGE TEST COMPLETED"
echo "=========================================="
```

## 🎯 Full System Verification

```bash
#!/bin/bash
# Complete System Verification Script

echo "🚀 STARTING FULL SYSTEM VERIFICATION"

# 1. Check all services are running
echo "1. Checking service status..."
curl -f http://localhost:8000/health || echo "❌ API Server down"
curl -f http://localhost:8005 || echo "❌ Streamlit Dashboard down"
redis-cli ping || echo "❌ Redis down"
pg_isready || echo "❌ PostgreSQL down"

# 2. Run OCR tests
echo "2. Testing OCR functionality..."
python test_ocr.py

# 3. Run multimodal analysis tests
echo "3. Testing multimodal AI analysis..."
python test_multimodal.py

# 4. Run ReAct decision tests
echo "4. Testing ReAct decision engine..."
python test_complete_workflow.py

# 5. Run API integration tests
echo "5. Running API integration tests..."
./api_coverage_test.sh

echo "✅ FULL SYSTEM VERIFICATION COMPLETED"
```