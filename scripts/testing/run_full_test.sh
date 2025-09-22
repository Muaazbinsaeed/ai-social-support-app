#!/bin/bash

# Complete End-to-End Test with Real Documents
# This script tests the entire AI workflow from document upload to decision making

set -e

echo "=========================================="
echo "🚀 FULL END-TO-END AI WORKFLOW TEST"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test documents (update paths as needed)
EMIRATES_ID_PATH="/Users/muaazbinsaeed/Downloads/Project/AI-social/docs/EmirateIDFront.jpg"
BANK_STATEMENT_PATH="/Users/muaazbinsaeed/Downloads/Project/AI-social/docs/Bank Muaaz Alfalah Statement.pdf"

# Check if test documents exist
check_documents() {
    echo -e "${YELLOW}📄 Checking test documents...${NC}"

    if [ -f "$EMIRATES_ID_PATH" ]; then
        echo -e "${GREEN}✅ Emirates ID found: $EMIRATES_ID_PATH${NC}"
    else
        echo -e "${RED}❌ Emirates ID not found: $EMIRATES_ID_PATH${NC}"
        echo "Please update EMIRATES_ID_PATH in the script"
        exit 1
    fi

    if [ -f "$BANK_STATEMENT_PATH" ]; then
        echo -e "${GREEN}✅ Bank Statement found: $BANK_STATEMENT_PATH${NC}"
    else
        echo -e "${RED}❌ Bank Statement not found: $BANK_STATEMENT_PATH${NC}"
        echo "Please update BANK_STATEMENT_PATH in the script"
        exit 1
    fi
    echo ""
}

# Setup test user
setup_user() {
    echo -e "${YELLOW}👤 Setting up test user...${NC}"

    TIMESTAMP=$(date +%s)
    USERNAME="e2e_test_$TIMESTAMP"
    EMAIL="e2e_test_$TIMESTAMP@example.com"

    # Register user
    echo "Registering user: $USERNAME"
    REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/register \
        -H "Content-Type: application/json" \
        -d '{
            "username": "'$USERNAME'",
            "email": "'$EMAIL'",
            "password": "SecurePass123",
            "full_name": "E2E Test User",
            "phone": "+971501234567",
            "emirates_id": "784-1995-1234567-8"
        }')

    USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.id')
    if [ "$USER_ID" = "null" ]; then
        echo -e "${RED}❌ Registration failed${NC}"
        echo "$REGISTER_RESPONSE" | jq
        exit 1
    fi

    # Login
    echo "Logging in user: $USERNAME"
    LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
        -H "Content-Type: application/json" \
        -d '{
            "username": "'$USERNAME'",
            "password": "SecurePass123"
        }')

    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
    if [ "$TOKEN" = "null" ]; then
        echo -e "${RED}❌ Login failed${NC}"
        echo "$LOGIN_RESPONSE" | jq
        exit 1
    fi

    echo -e "${GREEN}✅ User setup completed${NC}"
    echo -e "${BLUE}User ID: $USER_ID${NC}"
    echo -e "${BLUE}Token: ${TOKEN:0:50}...${NC}"
    echo ""
}

# Start application
start_application() {
    echo -e "${YELLOW}📝 Starting application...${NC}"

    APP_RESPONSE=$(curl -s -X POST http://localhost:8000/workflow/start-application \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "full_name": "E2E Test User",
            "emirates_id": "784-1995-1234567-8",
            "phone": "+971501234567",
            "email": "'$EMAIL'"
        }')

    APPLICATION_ID=$(echo "$APP_RESPONSE" | jq -r '.application_id')
    if [ "$APPLICATION_ID" = "null" ]; then
        echo -e "${RED}❌ Application creation failed${NC}"
        echo "$APP_RESPONSE" | jq
        exit 1
    fi

    echo -e "${GREEN}✅ Application created${NC}"
    echo -e "${BLUE}Application ID: $APPLICATION_ID${NC}"
    echo ""
}

# Upload documents
upload_documents() {
    echo -e "${YELLOW}📤 Uploading documents...${NC}"

    echo "Uploading Emirates ID and Bank Statement..."
    UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8000/workflow/upload-documents/$APPLICATION_ID \
        -H "Authorization: Bearer $TOKEN" \
        -F "emirates_id=@$EMIRATES_ID_PATH" \
        -F "bank_statement=@$BANK_STATEMENT_PATH")

    UPLOAD_STATUS=$(echo "$UPLOAD_RESPONSE" | jq -r '.status')
    DOCUMENT_IDS=$(echo "$UPLOAD_RESPONSE" | jq -r '.document_ids[]')

    if [ "$UPLOAD_STATUS" = "documents_uploaded" ]; then
        echo -e "${GREEN}✅ Documents uploaded successfully${NC}"
        echo -e "${BLUE}Document IDs: $DOCUMENT_IDS${NC}"
    else
        echo -e "${RED}❌ Document upload failed${NC}"
        echo "$UPLOAD_RESPONSE" | jq
        exit 1
    fi
    echo ""
}

# Start processing
start_processing() {
    echo -e "${YELLOW}⚙️  Starting AI processing...${NC}"

    PROCESS_RESPONSE=$(curl -s -X POST http://localhost:8000/workflow/process/$APPLICATION_ID \
        -H "Authorization: Bearer $TOKEN")

    PROCESS_STATUS=$(echo "$PROCESS_RESPONSE" | jq -r '.status')
    JOB_ID=$(echo "$PROCESS_RESPONSE" | jq -r '.processing_job_id')

    if [ "$PROCESS_STATUS" = "processing_started" ]; then
        echo -e "${GREEN}✅ Processing started${NC}"
        echo -e "${BLUE}Job ID: $JOB_ID${NC}"
    else
        echo -e "${RED}❌ Processing start failed${NC}"
        echo "$PROCESS_RESPONSE" | jq
        exit 1
    fi
    echo ""
}

# Monitor processing
monitor_processing() {
    echo -e "${YELLOW}👀 Monitoring processing progress...${NC}"

    MAX_ATTEMPTS=24  # 4 minutes max (24 * 10 seconds)
    ATTEMPT=1

    while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
        echo "Attempt $ATTEMPT/$MAX_ATTEMPTS - Checking status..."

        STATUS_RESPONSE=$(curl -s -X GET http://localhost:8000/workflow/status/$APPLICATION_ID \
            -H "Authorization: Bearer $TOKEN")

        CURRENT_STATE=$(echo "$STATUS_RESPONSE" | jq -r '.current_state')
        PROGRESS=$(echo "$STATUS_RESPONSE" | jq -r '.progress')

        echo -e "  Status: ${BLUE}$CURRENT_STATE${NC} (${BLUE}$PROGRESS%${NC})"

        # Check if processing is complete
        if [ "$CURRENT_STATE" = "completed" ]; then
            echo -e "${GREEN}✅ Processing completed successfully!${NC}"
            return 0
        elif [ "$CURRENT_STATE" = "failed" ]; then
            echo -e "${RED}❌ Processing failed${NC}"
            echo "$STATUS_RESPONSE" | jq
            return 1
        fi

        # Wait before next check
        sleep 10
        ATTEMPT=$((ATTEMPT + 1))
    done

    echo -e "${YELLOW}⏰ Processing timeout reached${NC}"
    echo "Current status: $CURRENT_STATE ($PROGRESS%)"
    return 1
}

# Get final results
get_results() {
    echo -e "${YELLOW}📋 Getting final results...${NC}"

    RESULTS_RESPONSE=$(curl -s -X GET http://localhost:8000/workflow/results/$APPLICATION_ID \
        -H "Authorization: Bearer $TOKEN")

    # Check if results are available
    if echo "$RESULTS_RESPONSE" | jq -e '.decision_outcome' > /dev/null 2>&1; then
        DECISION=$(echo "$RESULTS_RESPONSE" | jq -r '.decision_outcome')
        CONFIDENCE=$(echo "$RESULTS_RESPONSE" | jq -r '.confidence')
        BENEFIT_AMOUNT=$(echo "$RESULTS_RESPONSE" | jq -r '.benefit_amount // 0')

        echo -e "${GREEN}✅ Results obtained${NC}"
        echo -e "${BLUE}Decision: $DECISION${NC}"
        echo -e "${BLUE}Confidence: $CONFIDENCE${NC}"
        echo -e "${BLUE}Benefit Amount: AED $BENEFIT_AMOUNT${NC}"

        # Show reasoning if available
        if echo "$RESULTS_RESPONSE" | jq -e '.reasoning' > /dev/null 2>&1; then
            REASONING=$(echo "$RESULTS_RESPONSE" | jq -r '.reasoning.summary // "No summary available"')
            echo -e "${BLUE}Reasoning: $REASONING${NC}"
        fi

        echo ""
        echo -e "${GREEN}🎉 FULL WORKFLOW COMPLETED SUCCESSFULLY!${NC}"
        return 0
    else
        echo -e "${YELLOW}⏳ Results not ready yet${NC}"
        echo "$RESULTS_RESPONSE" | jq
        return 1
    fi
}

# Test AI components separately
test_ai_components() {
    echo -e "${YELLOW}🧠 Testing AI components separately...${NC}"

    # Test OCR
    echo "Testing OCR service..."
    if python3 test_ocr.py > /tmp/ocr_test.log 2>&1; then
        echo -e "${GREEN}✅ OCR test passed${NC}"
    else
        echo -e "${RED}❌ OCR test failed${NC}"
        tail -5 /tmp/ocr_test.log
    fi

    # Test multimodal analysis
    echo "Testing multimodal AI analysis..."
    if timeout 60 python3 test_multimodal.py > /tmp/multimodal_test.log 2>&1; then
        echo -e "${GREEN}✅ Multimodal test passed${NC}"
    else
        echo -e "${RED}❌ Multimodal test failed or timed out${NC}"
        tail -5 /tmp/multimodal_test.log
    fi

    echo ""
}

# Main execution
main() {
    echo "Starting comprehensive end-to-end test..."
    echo "Time: $(date)"
    echo ""

    # Pre-checks
    check_documents

    # Setup
    setup_user

    # Test AI components first
    test_ai_components

    # Run full workflow
    start_application
    upload_documents
    start_processing

    # Monitor and get results
    if monitor_processing; then
        sleep 5  # Give a moment for results to be ready
        get_results
    else
        echo -e "${RED}❌ Processing did not complete in time${NC}"
        echo ""
        echo -e "${YELLOW}Current application status:${NC}"
        curl -s -X GET http://localhost:8000/workflow/status/$APPLICATION_ID \
            -H "Authorization: Bearer $TOKEN" | jq
        exit 1
    fi

    echo ""
    echo -e "${BLUE}=========================================="
    echo "🏁 END-TO-END TEST COMPLETED"
    echo "===========================================${NC}"
}

# Cleanup function
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    rm -f /tmp/*_test.log
}

# Trap cleanup on exit
trap cleanup EXIT

# Check if server is running
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}❌ API server is not running on port 8000${NC}"
    echo "Please start the server first: uvicorn app.main:app --host 0.0.0.0 --port 8000"
    exit 1
fi

# Run main function
main "$@"