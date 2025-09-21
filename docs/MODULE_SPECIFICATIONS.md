# 🏗️ Module Specifications - Implementation Guide

**Version**: 4.0.0
**Last Updated**: 2025-09-21
**Purpose**: Detailed implementation specifications for each module

---

## 📋 **Module Implementation Standards**

### **Definition of Done (Per Module)**
- [ ] All APIs implemented and working (200/201 responses)
- [ ] Unit tests with 80%+ coverage
- [ ] API tests for all endpoints
- [ ] Integration tests passing
- [ ] Error handling implemented
- [ ] Logging added
- [ ] Documentation updated
- [ ] PROJECT_STATUS.md updated

---

## 🔐 **MODULE 1: User Management & Authentication**

### **📊 Current Status**
- **Implementation**: 90% complete
- **APIs**: 7/7 working
- **Tests**: 0% complete
- **Priority**: Immediate

### **🎯 Objectives**
1. Complete authentication testing suite
2. Add role-based access control
3. Implement password reset functionality
4. Add account activation workflow

### **📁 Files Structure**
```
app/user_management/
├── ✅ __init__.py
├── ✅ user_models.py          # User database model
├── ✅ user_service.py         # Business logic
├── ✅ auth_schemas.py         # Request/response models
└── 🔄 user_permissions.py    # Role-based access (NEW)

tests/module1_user_auth/
├── ❌ test_user_service.py    # Unit tests
├── ❌ test_auth_endpoints.py  # API tests
├── ❌ test_permissions.py     # Role tests
└── ❌ test_integration.py     # DB integration tests
```

### **🔧 API Specifications**

#### **Existing APIs (To Test)**
| Endpoint | Method | Current Status | Test Required |
|----------|--------|----------------|---------------|
| `/auth/register` | POST | ✅ Working | Unit + API tests |
| `/auth/login` | POST | ✅ Working | JWT validation tests |
| `/auth/me` | GET | ✅ Working | Auth middleware tests |
| `/auth/status` | GET | ✅ Working | Session tests |
| `/auth/password` | PUT | ✅ Working | Security tests |
| `/auth/logout` | POST | ✅ Working | Token invalidation tests |
| `/auth/refresh` | POST | ✅ Working | Token refresh tests |

#### **New APIs (To Implement)**
| Endpoint | Method | Purpose | Implementation |
|----------|--------|---------|----------------|
| `/auth/reset-password` | POST | Password reset request | Send reset email |
| `/auth/reset-password/confirm` | POST | Confirm password reset | Validate token + update |
| `/auth/activate/{token}` | GET | Account activation | Activate user account |
| `/auth/roles` | GET | List user roles | Return user permissions |

### **🧪 Testing Requirements**

#### **Unit Tests** (`test_user_service.py`)
```python
class TestUserService:
    def test_create_user_valid_data()
    def test_create_user_duplicate_email()
    def test_authenticate_valid_credentials()
    def test_authenticate_invalid_credentials()
    def test_generate_jwt_token()
    def test_validate_jwt_token()
    def test_hash_password()
    def test_verify_password()
```

#### **API Tests** (`test_auth_endpoints.py`)
```python
class TestAuthEndpoints:
    def test_register_success()
    def test_register_duplicate_user()
    def test_login_success()
    def test_login_invalid_credentials()
    def test_protected_route_with_token()
    def test_protected_route_without_token()
    def test_password_change()
    def test_logout()
```

### **🚀 Implementation Tasks**
1. **Create test suite structure** (1 hour)
2. **Write unit tests** (2 hours)
3. **Write API tests** (2 hours)
4. **Add role-based permissions** (2 hours)
5. **Implement password reset** (2 hours)
6. **Run tests and fix issues** (1 hour)

**Total Estimated Time**: 10 hours

---

## 📝 **MODULE 2: Application Management**

### **📊 Current Status**
- **Implementation**: 60% complete
- **APIs**: 4/7 partial
- **Tests**: 0% complete
- **Priority**: High

### **🎯 Critical Missing Components**
1. **State Machine**: 12-state workflow engine
2. **Workflow Orchestration**: Step-by-step processing
3. **Progress Tracking**: Real-time status updates
4. **Business Logic**: Eligibility rules integration

### **📁 Files to Create**
```
app/application_flow/
├── ✅ __init__.py
├── ✅ application_models.py       # Existing
├── ❌ state_manager.py            # 12-state machine (CRITICAL)
├── ❌ application_workflow.py     # Orchestration engine
├── ❌ application_service.py      # Business logic
├── ❌ application_schemas.py      # Request/response models
└── ❌ application_constants.py    # States, messages, rules

tests/module2_applications/
├── ❌ test_state_machine.py       # State transition tests
├── ❌ test_workflow.py            # Workflow orchestration tests
├── ❌ test_application_service.py # Business logic tests
├── ❌ test_application_api.py     # API endpoint tests
└── ❌ test_integration.py         # Full workflow integration
```

### **🔧 State Machine Specification**

#### **12 Application States**
```python
class ApplicationState(Enum):
    # Initial states
    DRAFT = "draft"
    FORM_SUBMITTED = "form_submitted"

    # Document processing states
    DOCUMENTS_UPLOADED = "documents_uploaded"
    SCANNING_DOCUMENTS = "scanning_documents"
    OCR_COMPLETED = "ocr_completed"

    # Analysis states
    ANALYZING_INCOME = "analyzing_income"
    ANALYZING_IDENTITY = "analyzing_identity"
    ANALYSIS_COMPLETED = "analysis_completed"

    # Decision states
    MAKING_DECISION = "making_decision"
    DECISION_COMPLETED = "decision_completed"

    # Final states
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    PARTIAL_SUCCESS = "partial_success"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
```

#### **State Transition Rules**
```python
VALID_TRANSITIONS = {
    "draft": ["form_submitted"],
    "form_submitted": ["documents_uploaded"],
    "documents_uploaded": ["scanning_documents"],
    "scanning_documents": ["ocr_completed", "needs_review"],
    "ocr_completed": ["analyzing_income", "analyzing_identity"],
    # ... complete transition mapping
}
```

### **🔧 API Specifications**

#### **APIs to Implement/Fix**
| Endpoint | Method | Status | Implementation Required |
|----------|--------|--------|------------------------|
| `/applications/create` | POST | ❌ Missing | Create with state machine |
| `/applications/{id}` | GET | ⚠️ Partial | Add state info |
| `/applications/{id}/submit` | PUT | ❌ Missing | State transition |
| `/applications/user/{id}` | GET | ⚠️ Partial | Filter by user |
| `/applications/{id}/state` | PUT | ❌ Missing | Manual state update |
| `/workflow/start-application` | POST | ✅ Working | Enhance with state |
| `/workflow/status/{id}` | GET | ✅ Working | Add progress % |

### **🧪 Testing Requirements**

#### **State Machine Tests**
```python
class TestStateMachine:
    def test_valid_state_transitions()
    def test_invalid_state_transitions()
    def test_progress_calculation()
    def test_state_history_tracking()
    def test_graceful_failure_states()
```

### **🚀 Implementation Tasks**
1. **Create state machine** (4 hours)
2. **Implement workflow orchestration** (3 hours)
3. **Create application service** (3 hours)
4. **Update API endpoints** (2 hours)
5. **Write comprehensive tests** (3 hours)
6. **Integration testing** (1 hour)

**Total Estimated Time**: 16 hours

---

## 📄 **MODULE 3: Document Processing & OCR**

### **📊 Current Status**
- **Implementation**: 70% complete
- **APIs**: 5/8 working
- **Tests**: 0% complete
- **Priority**: High

### **🎯 Critical Issues**
1. **OCR Dependencies**: EasyOCR installation/configuration
2. **Async Processing**: Celery task integration
3. **Error Handling**: Timeout and retry logic
4. **Progress Tracking**: Real-time status updates

### **📁 Files Status**
```
app/document_processing/
├── ✅ __init__.py
├── ✅ document_models.py         # Database models
├── ✅ document_service.py        # Basic service
├── ✅ document_schemas.py        # Pydantic models
├── ✅ ocr_service.py            # Needs dependency fix
├── ✅ multimodal_service.py     # Basic structure
└── 🔄 document_pipeline.py     # New: Processing pipeline

app/workers/
├── ✅ celery_app.py             # Basic setup
├── 🔄 document_worker.py        # Needs enhancement
└── 🔄 ocr_worker.py            # New: Dedicated OCR worker
```

### **🔧 Issues to Fix**

#### **OCR Dependency Issues**
```bash
# Current error: EasyOCR not properly installed
pip install easyocr torch torchvision
# OR alternative: paddleocr, tesseract
```

#### **APIs to Fix**
| Endpoint | Method | Current Issue | Fix Required |
|----------|--------|---------------|--------------|
| `/ocr/process/{id}` | POST | 422 Error | Fix EasyOCR setup |
| `/ocr/batch` | POST | Partial work | Add proper queuing |
| `/ocr/status/{id}` | GET | Missing | Implement status tracking |
| `/analysis/upload-and-analyze` | POST | 500 Error | Fix file handling |

### **🧪 Testing Requirements**
```python
class TestOCRService:
    def test_extract_text_from_pdf()
    def test_extract_text_from_image()
    def test_ocr_timeout_handling()
    def test_ocr_error_recovery()
    def test_batch_processing()
```

### **🚀 Implementation Tasks**
1. **Fix OCR dependencies** (2 hours)
2. **Enhance Celery workers** (3 hours)
3. **Add progress tracking** (2 hours)
4. **Error handling and retries** (2 hours)
5. **Testing suite** (3 hours)

**Total Estimated Time**: 12 hours

---

## 🤖 **MODULE 4: Multimodal Analysis**

### **📊 Current Status**
- **Implementation**: 30% complete
- **APIs**: 2/5 working
- **Tests**: 0% complete
- **Priority**: Medium

### **🎯 Missing Components**
1. **Document Analysis Pipeline**: Structured data extraction
2. **Ollama Integration**: Model setup and configuration
3. **Confidence Scoring**: Analysis quality metrics
4. **Result Storage**: Processed data persistence

### **🔧 Implementation Requirements**
```python
# Document analysis pipeline
class DocumentAnalyzer:
    def analyze_bank_statement(self, text: str) -> BankStatementData
    def analyze_emirates_id(self, text: str) -> EmiratesIDData
    def calculate_confidence(self, results: dict) -> float
    def extract_structured_data(self, raw_text: str) -> dict
```

### **🚀 Implementation Tasks**
1. **Setup Ollama models** (2 hours)
2. **Create analysis pipeline** (4 hours)
3. **Implement confidence scoring** (2 hours)
4. **Add result storage** (2 hours)
5. **Testing and validation** (3 hours)

**Total Estimated Time**: 13 hours

---

## ⚖️ **MODULE 5: AI Decision Engine**

### **📊 Current Status**
- **Implementation**: 40% complete
- **APIs**: 3/6 partial
- **Tests**: 0% complete
- **Priority**: High

### **🎯 Missing Components**
1. **Eligibility Calculation**: Income/asset thresholds
2. **Benefit Calculation**: Amount determination
3. **Decision Persistence**: Result storage
4. **Explanation Generation**: AI reasoning

### **🔧 Business Rules to Implement**
```python
class EligibilityRules:
    INCOME_THRESHOLD_AED = 4000
    BALANCE_THRESHOLD_AED = 1500

    def calculate_eligibility(self, income: float, balance: float) -> bool
    def calculate_benefit_amount(self, income: float) -> float
    def generate_explanation(self, decision: dict) -> str
```

### **🚀 Implementation Tasks**
1. **Implement eligibility logic** (3 hours)
2. **Add benefit calculation** (2 hours)
3. **Create decision persistence** (2 hours)
4. **Add explanation generation** (2 hours)
5. **Testing and validation** (3 hours)

**Total Estimated Time**: 12 hours

---

## 💬 **MODULE 6: Chatbot Integration**

### **📊 Current Status**
- **Implementation**: 85% complete
- **APIs**: 6/6 working
- **Tests**: 0% complete
- **Priority**: Low

### **🎯 Enhancements Needed**
1. **Application Context**: Integration with user applications
2. **Document Queries**: Support for document-related questions
3. **Decision Explanation**: AI decision reasoning

### **🚀 Implementation Tasks**
1. **Add application context** (2 hours)
2. **Implement document queries** (2 hours)
3. **Add decision explanations** (2 hours)
4. **Testing suite** (2 hours)

**Total Estimated Time**: 8 hours

---

## 📊 **Overall Implementation Timeline**

### **Week 1: Foundation**
- **Day 1**: Module 1 - User Management (10 hours)
- **Day 2**: Module 2 Part 1 - State Machine (8 hours)
- **Day 3**: Module 2 Part 2 - Workflow (8 hours)

### **Week 2: Processing**
- **Day 4**: Module 3 - Document/OCR (12 hours)
- **Day 5**: Module 4 - Multimodal Analysis (13 hours)

### **Week 3: Intelligence**
- **Day 6**: Module 5 - Decision Engine (12 hours)
- **Day 7**: Module 6 - Chatbot (8 hours)
- **Day 8**: Integration Testing (8 hours)

**Total Estimated Effort**: 79 hours (~2-3 weeks)

---

## 🎯 **Success Metrics**

### **Per Module**
- [ ] All APIs return 200/201 responses
- [ ] 80%+ test coverage
- [ ] Zero critical bugs
- [ ] Documentation complete

### **Overall System**
- [ ] End-to-end workflow functional
- [ ] Performance under 2 minutes per application
- [ ] 99%+ uptime during testing
- [ ] Production-ready deployment

---

**📋 Next Action: Start Module 1 implementation and testing**