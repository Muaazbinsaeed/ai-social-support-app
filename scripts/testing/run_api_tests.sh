#!/bin/bash

# AI Social Security System - Complete API Test Suite
# Run this script to test all APIs and verify system functionality

set -e  # Exit on any error

echo "=========================================="
echo "🚀 AI SOCIAL SECURITY SYSTEM - API TESTS"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test function
run_test() {
    local test_name="$1"
    local command="$2"
    local expected_status="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${BLUE}Testing: $test_name${NC}"

    # Run the command and capture both output and status
    if eval "$command" > /tmp/test_output 2>&1; then
        if [ -z "$expected_status" ] || grep -q "$expected_status" /tmp/test_output; then
            echo -e "${GREEN}✅ PASSED${NC}"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "${RED}❌ FAILED - Expected: $expected_status${NC}"
            cat /tmp/test_output | head -3
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo -e "${RED}❌ FAILED - Command failed${NC}"
        cat /tmp/test_output | head -3
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    echo ""
}

# Check if services are running
check_services() {
    echo -e "${YELLOW}🔍 Checking service availability...${NC}"

    # Check API server
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API Server (port 8000) - Running${NC}"
    else
        echo -e "${RED}❌ API Server (port 8000) - Not running${NC}"
        echo "Please start the API server: uvicorn app.main:app --host 0.0.0.0 --port 8000"
        exit 1
    fi

    # Check Streamlit dashboard
    if curl -f http://localhost:8005 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Streamlit Dashboard (port 8005) - Running${NC}"
    else
        echo -e "${YELLOW}⚠️  Streamlit Dashboard (port 8005) - Not running (optional)${NC}"
    fi

    echo ""
}

# Create test user and get token
setup_test_user() {
    echo -e "${YELLOW}👤 Setting up test user...${NC}"

    # Generate unique username
    TIMESTAMP=$(date +%s)
    TEST_USERNAME="api_test_$TIMESTAMP"
    TEST_EMAIL="test_$TIMESTAMP@example.com"

    # Register user
    REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/register \
        -H "Content-Type: application/json" \
        -d '{
            "username": "'$TEST_USERNAME'",
            "email": "'$TEST_EMAIL'",
            "password": "SecurePass123",
            "full_name": "API Test User",
            "phone": "+971501234567",
            "emirates_id": "784-1987-7777888-9"
        }')

    if echo "$REGISTER_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Test user registered: $TEST_USERNAME${NC}"
    else
        echo -e "${RED}❌ Failed to register test user${NC}"
        echo "$REGISTER_RESPONSE"
        exit 1
    fi

    # Login and get token
    LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
        -H "Content-Type: application/json" \
        -d '{
            "username": "'$TEST_USERNAME'",
            "password": "SecurePass123"
        }')

    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

    if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
        echo -e "${GREEN}✅ Token obtained successfully${NC}"
        echo -e "${BLUE}Token: ${TOKEN:0:50}...${NC}"
    else
        echo -e "${RED}❌ Failed to get token${NC}"
        echo "$LOGIN_RESPONSE"
        exit 1
    fi

    echo ""
}

# Health Check Tests
health_tests() {
    echo -e "${YELLOW}🏥 Running Health Check Tests...${NC}"

    run_test "Basic Health Check" \
        "curl -s http://localhost:8000/health" \
        "ok"

    run_test "Database Health Check" \
        "curl -s http://localhost:8000/health/db" \
        ""

    run_test "Redis Health Check" \
        "curl -s http://localhost:8000/health/redis" \
        ""
}

# Authentication Tests
auth_tests() {
    echo -e "${YELLOW}🔐 Running Authentication Tests...${NC}"

    # Test invalid registration
    run_test "Invalid Registration (missing fields)" \
        "curl -s -X POST http://localhost:8000/auth/register -H 'Content-Type: application/json' -d '{\"username\":\"test\"}'" \
        "VALIDATION_ERROR"

    # Test invalid login
    run_test "Invalid Login (wrong credentials)" \
        "curl -s -X POST http://localhost:8000/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"nonexistent\",\"password\":\"wrong\"}'" \
        "AUTHENTICATION_ERROR"

    # Test get current user with valid token
    run_test "Get Current User (with valid token)" \
        "curl -s -X GET http://localhost:8000/auth/me -H 'Authorization: Bearer $TOKEN'" \
        "$TEST_USERNAME"

    # Test unauthorized access
    run_test "Unauthorized Access (no token)" \
        "curl -s -X GET http://localhost:8000/auth/me" \
        "AUTHENTICATION_ERROR"
}

# Workflow Tests
workflow_tests() {
    echo -e "${YELLOW}🔄 Running Workflow Tests...${NC}"

    # Start application
    APP_RESPONSE=$(curl -s -X POST http://localhost:8000/workflow/start-application \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "full_name": "API Test User",
            "emirates_id": "784-1987-7777888-9",
            "phone": "+971501234567",
            "email": "'$TEST_EMAIL'"
        }')

    APP_ID=$(echo "$APP_RESPONSE" | jq -r '.application_id')

    if [ "$APP_ID" != "null" ] && [ -n "$APP_ID" ]; then
        echo -e "${GREEN}✅ Application created: $APP_ID${NC}"
    else
        echo -e "${RED}❌ Failed to create application${NC}"
        echo "$APP_RESPONSE"
        return 1
    fi

    run_test "Get Application Status" \
        "curl -s -X GET http://localhost:8000/workflow/status/$APP_ID -H 'Authorization: Bearer $TOKEN'" \
        "form_submitted"

    # Test unauthorized workflow access
    run_test "Unauthorized Workflow Access" \
        "curl -s -X GET http://localhost:8000/workflow/status/$APP_ID" \
        "AUTHENTICATION_ERROR"

    # Test invalid application ID
    run_test "Invalid Application ID" \
        "curl -s -X GET http://localhost:8000/workflow/status/invalid-id -H 'Authorization: Bearer $TOKEN'" \
        "NOT_FOUND"
}

# Document Tests (without actual files)
document_tests() {
    echo -e "${YELLOW}📄 Running Document Tests...${NC}"

    # Test upload without files
    run_test "Document Upload (missing files)" \
        "curl -s -X POST http://localhost:8000/workflow/upload-documents/test-id -H 'Authorization: Bearer $TOKEN'" \
        "422"

    # Test upload with invalid ID
    run_test "Document Upload (invalid application ID)" \
        "curl -s -X POST http://localhost:8000/workflow/upload-documents/invalid-id -H 'Authorization: Bearer $TOKEN' -F 'test=test'" \
        "NOT_FOUND"
}

# API Coverage Summary
coverage_summary() {
    echo -e "${YELLOW}📊 API Coverage Summary${NC}"
    echo "=================================="
    echo -e "Total Tests: ${BLUE}$TOTAL_TESTS${NC}"
    echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
    echo -e "Success Rate: ${BLUE}$(( PASSED_TESTS * 100 / TOTAL_TESTS ))%${NC}"
    echo ""

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
        return 0
    else
        echo -e "${RED}⚠️  Some tests failed. Check the output above.${NC}"
        return 1
    fi
}

# Test Cleanup
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up test data...${NC}"
    rm -f /tmp/test_output
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main execution
main() {
    echo "Starting comprehensive API test suite..."
    echo "Time: $(date)"
    echo ""

    # Setup
    check_services
    setup_test_user

    # Run test suites
    health_tests
    auth_tests
    workflow_tests
    document_tests

    # Summary
    coverage_summary

    # Cleanup
    cleanup

    echo ""
    echo -e "${BLUE}=========================================="
    echo "🏁 API TEST SUITE COMPLETED"
    echo "===========================================${NC}"
}

# Run main function
main "$@"