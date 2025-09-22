# Social Security AI Workflow Automation System - Master Specification Document

> **MASTER PROMPT DOCUMENT**: Complete technical specification for generating a production-ready AI-powered government social security application processing system.

---

## 📋 **PROJECT OVERVIEW & REQUIREMENTS**

### **Core Objective**
Build an AI-powered government social security application processing system that automates the traditional 5-20 day manual process into a **2-minute AI-driven workflow** with 99% automated decision-making capability.

### **Business Requirements**
- **Processing Time**: Reduce from 5-20 days to under 2 minutes
- **Automation Rate**: Achieve 99% automated decision-making
- **User Experience**: Professional dashboard with real-time status updates
- **Reliability**: Graceful failure handling with partial data processing
- **Scalability**: Handle 2-5 concurrent users initially
- **Compliance**: Government-grade security and audit trails

### **Functional Requirements**
1. **User Authentication**: JWT-based auth with test user accounts
2. **Application Management**: Create, submit, and track applications
3. **Document Processing**: Upload, OCR, and multimodal analysis of PDFs/images
4. **AI Decision Making**: Automated eligibility assessment with ReAct reasoning
5. **Status Tracking**: Real-time progress updates with detailed steps
6. **Graceful Degradation**: Continue processing with partial failures
7. **Dashboard Interface**: Three-panel layout with live updates

### **Technical Requirements**
- **Local AI Processing**: No external API dependencies
- **Container Deployment**: Full Docker Compose stack
- **Background Processing**: Async task processing with Celery
- **Database Support**: PostgreSQL + Qdrant vector database
- **File Management**: Organized storage with versioning
- **Health Monitoring**: Comprehensive system health checks

---

## 🏗️ **SYSTEM ARCHITECTURE & DESIGN**

### **High-Level Architecture Pattern**
```
┌─────────────────────────────────────────────────────────────┐
│                    USER ACCESS LAYER                       │
│             Streamlit Dashboard (Port 8005)                │
│        Three-Panel Layout with Real-Time Updates           │
└──────────────────────┬──────────────────────────────────────┘
                       │ Workflow-Based HTTP API Calls
┌──────────────────────▼──────────────────────────────────────┐
│                  SERVICE LAYER                              │
│              Single FastAPI Application (Port 8000)        │
│                                                             │
│  Flow-Based Architecture:                                   │
│  ├── user_management/     - Authentication & user flows    │
│  ├── application_flow/    - Application lifecycle          │  
│  ├── document_processing/ - Document upload & analysis     │
│  ├── decision_making/     - AI-powered eligibility         │
│  ├── shared/             - Common utilities                │
│  └── api/                - Workflow-based endpoints        │
│                                                             │
│  Background Workers (Celery):                              │
│  ├── Document processing with 5-minute timeout            │
│  ├── OCR + Multimodal analysis                            │
│  └── Graceful failure handling                            │
└─────────────────────────────────────────────────────────────┘
                       │ AI Model Inference
┌──────────────────────▼──────────────────────────────────────┐
│                   AI/ML LAYER                               │
│     Ollama Local LLM Server (Port 11434)                   │
│     ├── moondream:1.8b  - Multimodal document analysis     │
│     ├── qwen2:1.5b      - Decision making & reasoning      │
│     └── nomic-embed-text - Document embeddings             │
└─────────────────────────────────────────────────────────────┘
                       │ Data Persistence
┌──────────────────────▼──────────────────────────────────────┐
│                  DATA LAYER                                 │
│  ├── PostgreSQL (Port 5432) - Structured application data  │
│  ├── Redis (Port 6379)      - Cache + job queues          │
│  ├── Qdrant (Port 6333)     - Vector embeddings           │
│  └── Local Files            - Document storage             │
└─────────────────────────────────────────────────────────────┘
```

### **Component Interaction Diagram**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Dashboard  │───▶│   FastAPI   │───▶│   Celery    │───▶│   Ollama    │
│  Frontend   │    │     App     │    │   Worker    │    │   Models    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Session    │    │ PostgreSQL  │    │    Redis    │    │   Qdrant    │
│  State      │    │  Database   │    │   Queue     │    │   Vectors   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘

Flow: User Action → API Call → Background Task → AI Processing → Database Update → UI Update
```

### **Sophisticated State Machine Design**
```python
# Application Lifecycle States (12 detailed states)
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
    
    # Final states with graceful failure support
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"           # Graceful failure state
    PARTIAL_SUCCESS = "partial_success"     # Continue with available data
    MANUAL_REVIEW_REQUIRED = "manual_review_required"

# State transition messages for user feedback
STATE_MESSAGES = {
    "documents_uploaded": "📤 Documents received, starting analysis...",
    "scanning_documents": "🔍 Scanning documents for text extraction...",
    "analyzing_income": "💰 Analyzing bank statement - Income: $8,500",
    "analyzing_identity": "🆔 Verifying Emirates ID details...",  
    "making_decision": "⚖️ Evaluating eligibility criteria...",
    "needs_review": "👀 Partial data processed, manual review required",
    "approved": "🎉 APPROVED: Eligible for AED 2,500/month support"
}
```

### **Graceful Failure Handling Strategy**
```python
# Core principle: Continue processing even when components fail
# Implementation approach:
# 1. Try all processing steps independently
# 2. Collect partial results from successful steps
# 3. Make decisions based on available data
# 4. Mark low-confidence results for manual review
# 5. Provide detailed feedback on what succeeded/failed

# Example graceful failure scenarios:
# Scenario 1: OCR fails on bank statement, Emirates ID succeeds
#   → Continue with identity verification only
#   → Mark as "needs_review" with available identity data
# 
# Scenario 2: Multimodal analysis times out
#   → Use OCR text results only
#   → Lower confidence score, possible approval with caveats
# 
# Scenario 3: AI model unavailable
#   → Fall back to mock responses for development
#   → Continue workflow with synthetic data
```

---

## 🛠️ **TECHNOLOGY STACK & DEPENDENCIES**

### **Programming Languages & Versions**
- **Python**: 3.11 (primary language)
- **JavaScript**: ES2022 (for any custom Streamlit components)
- **SQL**: PostgreSQL dialect
- **YAML**: Docker Compose configuration
- **Shell**: Bash scripts for automation

### **Core Frameworks & Libraries**
```python
# Web Framework & API
fastapi==0.104.1              # High-performance async API framework
uvicorn==0.24.0               # ASGI server
pydantic==2.5.0               # Data validation and serialization

# Frontend & UI
streamlit==1.38.0             # Dashboard interface
plotly==5.17.0                # Interactive charts and visualizations

# Background Processing
celery==5.3.4                 # Distributed task queue
redis==5.0.1                  # Message broker and cache

# Database & ORM
sqlalchemy==2.0.23            # SQL toolkit and ORM
alembic==1.13.0               # Database migration tool
psycopg2-binary==2.9.9        # PostgreSQL adapter

# AI/ML & Document Processing
ollama==0.1.7                 # Local LLM client library
qdrant-client==1.6.4          # Vector database client
easyocr==1.7.0                # OCR processing
transformers==4.35.0          # Hugging Face transformers
torch==2.1.0                  # PyTorch for ML models

# Workflow & State Management
langgraph==0.0.40             # Workflow orchestration
langchain==0.1.0              # LLM application framework

# File Processing
PyMuPDF==1.23.8               # PDF processing
Pillow==10.1.0                # Image processing
python-multipart==0.0.6       # File upload handling

# Utilities & Logging
python-jose[cryptography]==3.3.0  # JWT handling
passlib[bcrypt]==1.7.4         # Password hashing
python-dotenv==1.0.0           # Environment variable management
structlog==23.2.0              # Structured logging
```

### **Infrastructure & DevOps**
```yaml
# Container Orchestration
docker: ">=24.0"
docker-compose: ">=2.20"

# Databases
postgresql: "15"
redis: "7-alpine"
qdrant: "latest"

# AI Model Server
ollama: "latest"

# System Requirements
os: "Linux/macOS/Windows with Docker support"
ram: "8GB minimum, 16GB recommended"
storage: "20GB for models and data"
cpu: "4+ cores recommended"
```

### **AI Models & Specifications**
```python
# Local LLM Models (via Ollama)
MODELS = {
    "multimodal_analysis": {
        "name": "moondream:1.8b",
        "size": "~1GB",
        "purpose": "Document understanding and structured data extraction",
        "performance": "20-35 seconds per document"
    },
    "decision_making": {
        "name": "qwen2:1.5b", 
        "size": "~800MB",
        "purpose": "Eligibility reasoning and decision making",
        "performance": "5-10 seconds per decision"
    },
    "embeddings": {
        "name": "nomic-embed-text",
        "size": "~500MB", 
        "purpose": "Document vectorization and similarity search",
        "performance": "1-2 seconds per document"
    }
}

# Model fallback strategy
# 1. Check model availability on startup
# 2. Auto-download missing models
# 3. Fall back to mock responses if models unavailable
# 4. Graceful degradation with confidence scoring
```

---

## 📁 **PROJECT STRUCTURE & FILE ORGANIZATION**

### **Complete Directory Structure**
```
social_security_ai/
├── README.md                          # Project documentation
├── docker-compose.yml                 # Container orchestration
├── docker-compose.dev.yml            # Development overrides
├── .env.example                       # Environment template
├── .env                               # Environment configuration (gitignored)
├── Dockerfile                         # Main application image
├── requirements.txt                   # Python dependencies
├── .gitignore                        # Version control exclusions
├── LICENSE                           # Project license
│
├── app/                              # Main FastAPI Application
│   ├── __init__.py
│   ├── main.py                       # FastAPI application entry point
│   ├── config.py                     # Configuration management
│   ├── dependencies.py               # Common dependencies (auth, db)
│   │
│   ├── user_management/              # User Authentication & Management
│   │   ├── __init__.py
│   │   ├── auth_flow.py             # Login/logout workflow
│   │   ├── user_service.py          # User business logic
│   │   ├── user_models.py           # User SQLAlchemy models
│   │   └── auth_schemas.py          # Pydantic request/response models
│   │
│   ├── application_flow/             # Application Lifecycle Management
│   │   ├── __init__.py
│   │   ├── application_workflow.py  # Main application workflow
│   │   ├── state_manager.py         # State machine implementation
│   │   ├── application_service.py   # Application business logic
│   │   ├── application_models.py    # Application SQLAlchemy models
│   │   └── application_schemas.py   # Application Pydantic models
│   │
│   ├── document_processing/          # Document Upload & Analysis
│   │   ├── __init__.py
│   │   ├── upload_flow.py           # Document upload workflow
│   │   ├── processing_flow.py       # OCR and analysis pipeline
│   │   ├── document_service.py      # Document business logic
│   │   ├── ocr_service.py           # EasyOCR integration
│   │   ├── multimodal_service.py    # Ollama multimodal analysis
│   │   ├── document_models.py       # Document SQLAlchemy models
│   │   └── document_schemas.py      # Document Pydantic models
│   │
│   ├── decision_making/              # AI-Powered Decision Engine
│   │   ├── __init__.py
│   │   ├── eligibility_flow.py      # Decision workflow
│   │   ├── decision_service.py      # Decision business logic
│   │   ├── react_reasoning.py       # ReAct framework implementation
│   │   ├── decision_models.py       # Decision SQLAlchemy models
│   │   └── decision_schemas.py      # Decision Pydantic models
│   │
│   ├── shared/                       # Shared Utilities & Services
│   │   ├── __init__.py
│   │   ├── database.py              # SQLAlchemy database setup
│   │   ├── logging_config.py        # Structured logging configuration
│   │   ├── llm_client.py            # Ollama client with fallback
│   │   ├── file_utils.py            # File handling utilities
│   │   ├── workflow_base.py         # Base workflow class
│   │   └── exceptions.py            # Custom exception classes
│   │
│   ├── workers/                      # Background Task Processing
│   │   ├── __init__.py
│   │   ├── celery_app.py            # Celery configuration
│   │   ├── document_worker.py       # Document processing tasks
│   │   ├── decision_worker.py       # Decision making tasks
│   │   └── cleanup_worker.py        # Maintenance tasks
│   │
│   └── api/                          # API Endpoints & Routing
│       ├── __init__.py
│       ├── workflow_router.py       # Main workflow endpoints
│       ├── status_router.py         # Status tracking endpoints
│       ├── health_router.py         # Health check endpoints
│       ├── auth_router.py           # Authentication endpoints
│       └── admin_router.py          # Admin/debug endpoints
│
├── frontend/                         # Streamlit Dashboard Application
│   ├── __init__.py
│   ├── dashboard_app.py             # Main dashboard entry point
│   ├── components/                  # Reusable UI components
│   │   ├── __init__.py
│   │   ├── auth_component.py        # Login/logout component
│   │   ├── application_panel.py     # Left panel - application form
│   │   ├── document_panel.py        # Center panel - document upload
│   │   ├── status_panel.py          # Right panel - processing status
│   │   ├── results_panel.py         # Bottom panel - results display
│   │   └── chat_component.py        # Chat interface component
│   ├── utils/                       # Frontend utilities
│   │   ├── __init__.py
│   │   ├── api_client.py            # HTTP client for FastAPI
│   │   ├── dashboard_state.py       # Dashboard state management
│   │   ├── formatting_utils.py      # Data formatting helpers
│   │   └── validation_utils.py      # Client-side validation
│   └── styles/                      # Custom CSS and styling
│       ├── dashboard.css            # Main dashboard styles
│       └── components.css           # Component-specific styles
│
├── scripts/                          # Automation & Setup Scripts
│   ├── __init__.py
│   ├── init_db.py                   # Database initialization
│   ├── seed_users.py                # Create test user accounts
│   ├── generate_test_data.py        # Create synthetic documents
│   ├── reset_system.py              # Development environment reset
│   ├── health_check.py              # System health verification
│   ├── backup_data.py               # Data backup procedures
│   └── cleanup_files.py             # File cleanup utilities
│
├── uploads/                          # Document Storage
│   ├── .gitkeep
│   └── {application_id}/            # Application-specific folders
│       ├── bank_statement_20241219_143022.pdf
│       └── emirates_id_20241219_143030.jpg
│
├── logs/                             # Application Logs
│   ├── .gitkeep
│   ├── app.log                      # Main application logs
│   ├── worker.log                   # Background worker logs
│   ├── error.log                    # Error logs
│   └── access.log                   # API access logs
│
├── tests/                            # Test Suite
│   ├── __init__.py
│   ├── conftest.py                  # PyTest configuration and fixtures
│   ├── unit/                        # Unit tests
│   │   ├── test_user_service.py
│   │   ├── test_application_service.py
│   │   ├── test_document_service.py
│   │   └── test_decision_service.py
│   ├── integration/                 # Integration tests
│   │   ├── test_workflow_integration.py
│   │   ├── test_api_endpoints.py
│   │   └── test_graceful_failure.py
│   ├── fixtures/                    # Test data and fixtures
│   │   ├── sample_bank_statement.pdf
│   │   ├── sample_emirates_id.jpg
│   │   └── mock_responses.json
│   └── performance/                 # Performance tests
│       ├── test_processing_time.py
│       └── test_concurrent_users.py
│
├── docs/                             # Additional Documentation
│   ├── api_specification.md         # OpenAPI documentation
│   ├── deployment_guide.md          # Deployment instructions
│   ├── development_guide.md         # Development workflow
│   └── architecture_decisions.md    # ADR documentation
│
└── infrastructure/                   # Infrastructure as Code
    ├── nginx/                       # Nginx configuration
    │   └── nginx.conf
    ├── monitoring/                  # Monitoring configuration
    │   ├── prometheus.yml
    │   └── grafana_dashboard.json
    └── backup/                      # Backup scripts and configs
        ├── backup_script.sh
        └── restore_script.sh
```

---

## 🎨 **USER INTERFACE & DASHBOARD DESIGN**

### **Dashboard Layout Specification**
```
┌─────────────────────────────────────────────────────────────┐
│                    Social Security AI                      │
│                   [User: user1] [Logout]                   │
├─────────────────┬─────────────────┬─────────────────────────┤
│   APPLICATION   │   DOCUMENTS     │    PROCESSING STATUS    │
│     FORM        │    UPLOAD       │                         │
│   (Left Panel)  │ (Center Panel)  │    (Right Panel)        │
├─────────────────┼─────────────────┼─────────────────────────┤
│ Full Name:      │ 📄 Bank Stmt    │ Progress: [████████░░]  │
│ [Ahmad Ali    ] │ ✅ bank_stmt.pdf │ 80% Complete            │
│                 │ 📁 2.1MB        │                         │
│ Emirates ID:    │ ⏱️ Processing... │ Current Step:           │
│ [784-1990-123 ] │                 │ ◐ Analyzing Income      │
│                 │ 🆔 Emirates ID  │                         │
│ Phone Number:   │ ❌ No file      │ Completed Steps:        │
│ [+971501234567] │ [Upload File]   │ ✅ Form Submitted       │
│                 │                 │ ✅ Documents Uploaded   │
│ Email Address:  │ 📊 Analysis     │ ✅ OCR Processing       │
│ [ahmad@test.com]│ Income: $8,500  │ ◐ Income Analysis       │
│                 │ Confidence: 95% │ ⏳ Decision Making      │
│ [Submit Form]   │ [View Details]  │                         │
│ [Save Draft]    │ [Retry Failed]  │ ⏱️ Est. Time: 45 sec    │
├─────────────────┴─────────────────┴─────────────────────────┤
│                    DECISION RESULTS                         │
│                                                             │
│ 🎉 DECISION: APPROVED                                       │
│ 💰 Benefit Amount: AED 2,500/month                         │
│ 📅 Effective Date: January 1, 2025                         │
│ 📋 Next Steps:                                             │
│   • Visit local office within 7 days                      │
│   • Bring original documents for verification             │
│   • Bank account setup for direct deposit                 │
│                                                             │
│ 📞 Questions? Contact: +971-4-123-4567                     │
│ 💬 [Chat Support] [Download Certificate] [Print Results]   │
└─────────────────────────────────────────────────────────────┘
```

### **UI Component Specifications**

#### **Left Panel: Application Form**
```python
# Required form fields with validation
FORM_FIELDS = {
    "full_name": {
        "type": "text",
        "required": True,
        "max_length": 255,
        "validation": "^[a-zA-Z\s]+$"  # Letters and spaces only
    },
    "emirates_id": {
        "type": "text", 
        "required": True,
        "format": "784-YYYY-XXXXXXX-X",
        "validation": "^784-[0-9]{4}-[0-9]{7}-[0-9]$"
    },
    "phone": {
        "type": "text",
        "required": True,
        "format": "+971XXXXXXXXX or 05XXXXXXXX",
        "validation": "^(\+971|05)[0-9]{8,9}$"
    },
    "email": {
        "type": "email",
        "required": True,
        "validation": "^[^@]+@[^@]+\.[^@]+$"
    }
}

# Form behavior
# - Real-time validation with error messages
# - Save draft functionality (auto-save every 30 seconds)
# - Form state persistence across page refreshes
# - Disable form after submission (prevent double submission)
```

#### **Center Panel: Document Upload**
```python
# Document upload specifications
DOCUMENT_REQUIREMENTS = {
    "bank_statement": {
        "required": True,
        "formats": ["PDF"],
        "max_size": "50MB",
        "description": "Last 3 months bank statement"
    },
    "emirates_id": {
        "required": True,
        "formats": ["PDF", "JPG", "PNG"],
        "max_size": "50MB", 
        "description": "Clear photo or scan of Emirates ID"
    }
}

# Upload behavior
# - Drag and drop interface with file preview
# - Progress bar during upload
# - File validation (size, type, content)
# - Versioning with timestamps for re-uploads
# - Preview functionality for uploaded files
# - Retry mechanism for failed uploads
```

#### **Right Panel: Processing Status**
```python
# Status display requirements
STATUS_DISPLAY = {
    "progress_bar": {
        "type": "horizontal_progress",
        "range": "0-100%",
        "color_coding": {
            "0-30%": "blue",    # Starting
            "31-70%": "orange", # Processing  
            "71-99%": "yellow", # Almost done
            "100%": "green"     # Complete
        }
    },
    "step_indicators": {
        "completed": "✅ Step Name - Details",
        "in_progress": "◐ Step Name - Current action", 
        "pending": "⏳ Step Name - Waiting",
        "failed": "❌ Step Name - Error message",
        "needs_review": "👀 Step Name - Manual review required"
    },
    "real_time_updates": {
        "polling_interval": "5 seconds",
        "auto_refresh": True,
        "progress_animation": True
    }
}
```

### **Responsive Design Requirements**
- **Desktop**: Three-panel layout (minimum 1200px width)
- **Tablet**: Two-panel layout with collapsible sections (768-1199px)
- **Mobile**: Single-panel accordion-style layout (< 768px)
- **Accessibility**: WCAG 2.1 AA compliance with screen reader support

---

## 🔄 **WORKFLOW SPECIFICATIONS & USE CASES**

### **Primary User Stories**

#### **User Story 1: New Application Submission**
```
As a UAE resident in need of social support,
I want to submit an application online with my documents,
So that I can receive a decision within minutes instead of waiting weeks.

Acceptance Criteria:
- I can create an account and login securely
- I can fill out the application form with validation
- I can upload my bank statement and Emirates ID
- I can see real-time progress of my application processing
- I receive a clear approval/rejection decision with explanation
- The entire process completes in under 5 minutes
```

#### **User Story 2: Application Status Tracking**
```
As an applicant who has submitted documents,
I want to see detailed progress of my application processing,
So that I know what's happening and when to expect results.

Acceptance Criteria:
- I can see each processing step with clear status indicators
- I receive specific feedback like "Income analyzed: $8,500"
- I can see estimated completion time
- I'm notified immediately when processing completes
- I can access my results anytime by logging back in
```

#### **User Story 3: Error Recovery**
```
As an applicant whose document processing failed,
I want to understand what went wrong and retry,
So that I can still receive a decision without starting over.

Acceptance Criteria:
- I see clear error messages about what failed
- I can retry specific steps without losing progress
- I receive partial results when some processing succeeds
- I'm guided on next steps for manual review when needed
- I maintain access to all previously submitted information
```

### **Detailed Workflow Specifications**

#### **Workflow 1: Complete Application Process**
```python
# Step-by-step workflow with timing and error handling
COMPLETE_WORKFLOW = {
    "step_1_authentication": {
        "duration": "10-30 seconds",
        "actions": ["Login with username/password", "Validate JWT token"],
        "success_criteria": ["Valid authentication token received"],
        "error_handling": ["Invalid credentials → Show error", "System error → Retry"]
    },
    "step_2_form_submission": {
        "duration": "2-5 minutes (user dependent)",
        "actions": ["Fill form fields", "Validate data", "Submit application"],
        "success_criteria": ["All required fields valid", "Application ID generated"],
        "error_handling": ["Validation error → Show field errors", "Submit error → Retry"]
    },
    "step_3_document_upload": {
        "duration": "1-3 minutes (user dependent)", 
        "actions": ["Select files", "Upload with progress", "Store with versioning"],
        "success_criteria": ["Files uploaded successfully", "File metadata stored"],
        "error_handling": ["Upload failure → Retry", "Invalid file → Show error"]
    },
    "step_4_background_processing": {
        "duration": "30-90 seconds",
        "actions": ["OCR processing", "Multimodal analysis", "Data extraction"],
        "success_criteria": ["Text extracted", "Structured data created"],
        "error_handling": ["Partial failure → Continue with available data"]
    },
    "step_5_decision_making": {
        "duration": "10-30 seconds",
        "actions": ["Analyze extracted data", "Apply eligibility rules", "Generate decision"],
        "success_criteria": ["Decision made with confidence score"],
        "error_handling": ["Low confidence → Mark for manual review"]
    },
    "step_6_result_display": {
        "duration": "Immediate",
        "actions": ["Update UI", "Show decision", "Provide next steps"],
        "success_criteria": ["Clear decision displayed", "Next steps provided"],
        "error_handling": ["Display error → Show generic success message"]
    }
}
```

#### **Workflow 2: Graceful Failure Handling**
```python
# Detailed graceful failure scenarios and responses
GRACEFUL_FAILURE_SCENARIOS = {
    "scenario_1_ocr_failure": {
        "trigger": "OCR processing fails or times out",
        "response": [
            "Log error with details",
            "Attempt basic text extraction", 
            "Continue with partial data",
            "Mark application as 'needs_review'",
            "Notify user of partial processing"
        ],
        "user_message": "Document scanning partially completed. Manual review required.",
        "next_steps": ["Admin review", "User resubmission option"]
    },
    "scenario_2_ai_model_unavailable": {
        "trigger": "Ollama service down or model not loaded",
        "response": [
            "Detect model unavailability",
            "Switch to mock response mode",
            "Continue workflow with synthetic data",
            "Flag results as 'system_generated'",
            "Process application normally"
        ],
        "user_message": "Processing completed with system assistance.",
        "next_steps": ["Normal approval process", "No user action required"]
    },
    "scenario_3_partial_document_success": {
        "trigger": "One document processes successfully, other fails",
        "response": [
            "Save successful processing results",
            "Calculate confidence with available data",
            "Make decision if confidence > 70%",
            "Otherwise mark for manual review",
            "Show user what succeeded/failed"
        ],
        "user_message": "Bank statement analyzed successfully. Emirates ID needs manual verification.",
        "next_steps": ["Conditional approval", "Document resubmission"]
    }
}
```

### **Edge Cases & Error Scenarios**

#### **Technical Edge Cases**
```python
EDGE_CASES = {
    "extremely_large_files": {
        "scenario": "User uploads 50MB bank statement PDF",
        "handling": [
            "Validate file size before processing",
            "Stream processing for large files", 
            "Timeout protection (5 minutes max)",
            "Memory management during OCR",
            "User feedback on processing time"
        ]
    },
    "corrupted_documents": {
        "scenario": "Uploaded PDF is corrupted or password protected",
        "handling": [
            "Detect file corruption early",
            "Provide specific error message",
            "Allow immediate re-upload",
            "Don't lose other form data",
            "Guide user on file requirements"
        ]
    },
    "concurrent_submissions": {
        "scenario": "User submits multiple applications simultaneously",
        "handling": [
            "Prevent double submission with UI state",
            "Database constraints on unique applications",
            "Clear error messages for duplicates",
            "Allow viewing existing application",
            "Graceful handling of race conditions"
        ]
    },
    "system_resource_exhaustion": {
        "scenario": "Multiple users processing documents simultaneously",
        "handling": [
            "Queue management with limits",
            "Graceful degradation messages",
            "Estimated wait time display",
            "Priority processing for retries",
            "Resource monitoring and alerts"
        ]
    }
}
```

#### **Business Logic Edge Cases**
```python
BUSINESS_EDGE_CASES = {
    "borderline_eligibility": {
        "scenario": "Applicant income is exactly at threshold (AED 4,000)",
        "handling": [
            "Apply consistent rounding rules",
            "Document decision reasoning clearly", 
            "Flag for supervisor review if configured",
            "Provide appeal process information",
            "Log decision factors for audit"
        ]
    },
    "missing_required_data": {
        "scenario": "Document extracted but missing key information",
        "handling": [
            "Clearly identify missing data points",
            "Allow selective document re-upload",
            "Provide guidance on required information",
            "Maintain partial progress", 
            "Enable manual data entry option"
        ]
    },
    "contradictory_information": {
        "scenario": "Bank statement shows different name than Emirates ID",
        "handling": [
            "Flag discrepancy for manual review",
            "Show user the conflicting information",
            "Provide clear next steps",
            "Allow document replacement",
            "Maintain audit trail of changes"
        ]
    }
}
```

---

## 🔌 **API SPECIFICATIONS & ENDPOINTS**

### **API Design Principles**
- **Workflow-Based**: Endpoints organized around user workflows, not resources
- **RESTful with RPC Elements**: REST for data operations, RPC for workflow actions
- **Consistent Response Format**: Standardized response structure across all endpoints
- **Detailed Error Messages**: Clear, actionable error information
- **Version Support**: API versioning for future compatibility

### **Complete API Specification**

#### **Authentication Endpoints**
```python
# POST /auth/register
{
    "endpoint": "/auth/register",
    "method": "POST",
    "description": "Register new user account",
    "request": {
        "username": "string (3-50 chars, alphanumeric)",
        "email": "string (valid email format)",
        "password": "string (6+ chars)",
        "full_name": "string (optional)"
    },
    "responses": {
        "201": {
            "user_id": "uuid",
            "username": "string",
            "email": "string",
            "message": "User registered successfully"
        },
        "400": {
            "error": "validation_failed",
            "details": {"field": "error_message"},
            "message": "Registration data invalid"
        },
        "409": {
            "error": "user_exists", 
            "message": "Username or email already registered"
        }
    }
}

# POST /auth/login  
{
    "endpoint": "/auth/login",
    "method": "POST",
    "description": "Authenticate user and return JWT token",
    "request": {
        "username": "string (username or email)",
        "password": "string"
    },
    "responses": {
        "200": {
            "access_token": "string (JWT)",
            "token_type": "bearer",
            "expires_in": 86400,
            "user_info": {
                "user_id": "uuid",
                "username": "string",
                "email": "string"
            }
        },
        "401": {
            "error": "invalid_credentials",
            "message": "Invalid username or password"
        },
        "429": {
            "error": "rate_limited", 
            "message": "Too many login attempts. Please try again later."
        }
    }
}
```

#### **Workflow Endpoints**
```python
# POST /workflow/start-application
{
    "endpoint": "/workflow/start-application",
    "method": "POST", 
    "description": "Initialize new application workflow",
    "authentication": "required (JWT Bearer token)",
    "request": {
        "full_name": "string (required)",
        "emirates_id": "string (format: 784-YYYY-XXXXXXX-X)",
        "phone": "string (UAE format)",
        "email": "string (valid email)"
    },
    "responses": {
        "201": {
            "application_id": "uuid",
            "status": "form_submitted",
            "progress": 20,
            "message": "Application created successfully",
            "next_steps": ["Upload required documents"],
            "expires_at": "2024-12-26T14:30:00Z"
        },
        "400": {
            "error": "validation_failed",
            "details": {
                "emirates_id": "Invalid Emirates ID format",
                "phone": "Invalid phone number format"
            }
        },
        "409": {
            "error": "application_exists",
            "message": "Active application already exists for this user",
            "existing_application_id": "uuid"
        }
    }
}

# POST /workflow/upload-documents/{application_id}
{
    "endpoint": "/workflow/upload-documents/{application_id}",
    "method": "POST",
    "description": "Upload and process application documents",
    "authentication": "required",
    "content_type": "multipart/form-data",
    "request": {
        "bank_statement": "file (PDF, max 50MB)",
        "emirates_id": "file (PDF/JPG/PNG, max 50MB)"
    },
    "responses": {
        "202": {
            "application_id": "uuid",
            "document_ids": ["uuid1", "uuid2"],
            "status": "documents_uploaded",
            "progress": 40,
            "processing_started": true,
            "estimated_completion": "90 seconds",
            "message": "Documents uploaded successfully, processing started"
        },
        "400": {
            "error": "invalid_files",
            "details": {
                "bank_statement": "File too large (52MB > 50MB limit)",
                "emirates_id": "Invalid file type (only PDF/JPG/PNG allowed)"
            }
        },
        "404": {
            "error": "application_not_found",
            "message": "Application not found or not accessible"
        },
        "409": {
            "error": "already_processing",
            "message": "Documents are already being processed for this application"
        }
    }
}

# GET /workflow/status/{application_id}
{
    "endpoint": "/workflow/status/{application_id}",
    "method": "GET",
    "description": "Get detailed processing status and progress",
    "authentication": "required",
    "responses": {
        "200": {
            "application_id": "uuid",
            "current_state": "analyzing_income",
            "progress": 75,
            "processing_time_elapsed": "65 seconds",
            "estimated_completion": "25 seconds",
            "steps": [
                {
                    "name": "form_submitted",
                    "status": "completed",
                    "message": "✅ Application form received and validated",
                    "completed_at": "2024-12-19T14:30:22Z",
                    "duration": "2 seconds"
                },
                {
                    "name": "documents_uploaded",
                    "status": "completed", 
                    "message": "✅ 2 documents uploaded successfully",
                    "completed_at": "2024-12-19T14:30:45Z",
                    "duration": "23 seconds"
                },
                {
                    "name": "scanning_documents", 
                    "status": "completed",
                    "message": "✅ Documents scanned and text extracted",
                    "completed_at": "2024-12-19T14:31:10Z",
                    "duration": "25 seconds"
                },
                {
                    "name": "analyzing_income",
                    "status": "in_progress",
                    "message": "💰 Analyzing bank statement - Income detected: $8,500",
                    "started_at": "2024-12-19T14:31:15Z",
                    "progress": 60
                },
                {
                    "name": "analyzing_identity",
                    "status": "pending",
                    "message": "⏳ Waiting to verify Emirates ID details"
                },
                {
                    "name": "making_decision",
                    "status": "pending", 
                    "message": "⏳ Ready to evaluate eligibility criteria"
                }
            ],
            "partial_results": {
                "documents_processed": 1,
                "bank_statement": {
                    "monthly_income": 8500,
                    "account_balance": 15000,
                    "confidence": 0.95,
                    "processing_time": "25 seconds"
                }
            },
            "errors": [],
            "can_retry": false,
            "next_action": "continue_processing"
        }
    }
}

# POST /workflow/process/{application_id}
{
    "endpoint": "/workflow/process/{application_id}",
    "method": "POST",
    "description": "Start or retry application processing workflow",
    "authentication": "required",
    "request": {
        "force_retry": "boolean (optional, default: false)",
        "retry_failed_steps": "boolean (optional, default: false)"
    },
    "responses": {
        "202": {
            "application_id": "uuid",
            "status": "processing_started",
            "message": "Processing workflow initiated",
            "estimated_completion": "90 seconds",
            "processing_job_id": "uuid"
        },
        "400": {
            "error": "invalid_state",
            "message": "Application not ready for processing",
            "current_state": "draft",
            "required_state": "documents_uploaded"
        },
        "409": {
            "error": "already_processing",
            "message": "Application is already being processed",
            "current_status": "analyzing_income"
        }
    }
}
```

#### **Status and Health Endpoints**
```python
# GET /health
{
    "endpoint": "/health",
    "method": "GET",
    "description": "Comprehensive system health check",
    "authentication": "not_required",
    "responses": {
        "200": {
            "status": "healthy",
            "timestamp": "2024-12-19T14:30:00Z",
            "services": {
                "database": {
                    "status": "healthy",
                    "response_time": "5ms",
                    "connection_pool": "8/20 connections used"
                },
                "redis": {
                    "status": "healthy", 
                    "response_time": "2ms",
                    "memory_usage": "45MB"
                },
                "ollama": {
                    "status": "healthy",
                    "models_loaded": ["moondream:1.8b", "qwen2:1.5b"],
                    "gpu_memory": "3.2GB used / 8GB total"
                },
                "celery_workers": {
                    "status": "healthy",
                    "active_workers": 2,
                    "queue_length": 3,
                    "failed_tasks": 0
                },
                "file_system": {
                    "status": "healthy",
                    "uploads_disk_usage": "2.1GB / 50GB",
                    "logs_disk_usage": "150MB / 10GB"
                }
            },
            "metrics": {
                "total_applications": 1247,
                "processing_success_rate": "97.3%",
                "average_processing_time": "67 seconds",
                "active_users": 3
            }
        },
        "503": {
            "status": "unhealthy",
            "failing_services": ["ollama", "celery_workers"],
            "errors": {
                "ollama": "Models not loaded",
                "celery_workers": "No active workers"
            },
            "impact": "New applications cannot be processed"
        }
    }
}

# GET /applications/{application_id}/results
{
    "endpoint": "/applications/{application_id}/results",
    "method": "GET",
    "description": "Get final application decision and results",
    "authentication": "required",
    "responses": {
        "200": {
            "application_id": "uuid",
            "decision": {
                "outcome": "approved",
                "confidence": 0.92,
                "benefit_amount": 2500,
                "currency": "AED",
                "frequency": "monthly",
                "effective_date": "2025-01-01",
                "review_date": "2025-07-01"
            },
            "reasoning": {
                "income_analysis": "Monthly income of AED 8,500 meets eligibility threshold",
                "document_verification": "Emirates ID verified successfully",
                "risk_assessment": "Low risk profile based on stable employment",
                "eligibility_score": 92
            },
            "next_steps": [
                "Visit local office within 7 days with original documents",
                "Set up direct deposit for benefit payments", 
                "Attend mandatory orientation session"
            ],
            "contact_information": {
                "office_address": "Social Security Office, Dubai",
                "phone": "+971-4-123-4567",
                "email": "support@socialsecurity.gov.ae"
            },
            "appeal_process": {
                "deadline": "2025-01-19T23:59:59Z",
                "process": "Submit written appeal with supporting documents",
                "contact": "appeals@socialsecurity.gov.ae"
            }
        },
        "202": {
            "status": "processing",
            "message": "Application still being processed",
            "estimated_completion": "45 seconds"
        }
    }
}
```

---

## 🧪 **TESTING SPECIFICATIONS**

### **Testing Strategy & Approach**
```python
TESTING_STRATEGY = {
    "testing_pyramid": {
        "unit_tests": {
            "percentage": "60%",
            "scope": "Individual functions and classes",
            "frameworks": ["pytest", "unittest.mock"],
            "coverage_target": "90%+"
        },
        "integration_tests": {
            "percentage": "30%",
            "scope": "Service interactions and workflows",
            "frameworks": ["pytest-asyncio", "httpx"],
            "coverage_target": "80%+"
        },
        "e2e_tests": {
            "percentage": "10%",
            "scope": "Complete user workflows",
            "frameworks": ["selenium", "playwright"],
            "coverage_target": "Major user paths"
        }
    },
    "test_data_strategy": {
        "synthetic_documents": "Generated PDFs and images for testing",
        "mock_ai_responses": "Predefined responses for AI model calls",
        "test_users": "Pre-seeded user accounts for testing",
        "database_fixtures": "Known-state database for predictable tests"
    }
}
```

### **Comprehensive Test Cases**

#### **Unit Test Specifications**
```python
# tests/unit/test_document_service.py
UNIT_TEST_CASES = {
    "test_document_upload_validation": {
        "description": "Validate document upload requirements",
        "test_cases": [
            {
                "name": "test_valid_pdf_upload",
                "input": "valid_bank_statement.pdf (2MB)",
                "expected": "successful validation",
                "assertions": ["file_size_valid", "file_type_valid", "content_readable"]
            },
            {
                "name": "test_oversized_file_rejection", 
                "input": "large_document.pdf (60MB)",
                "expected": "validation_error",
                "assertions": ["error_code == 'FILE_TOO_LARGE'", "max_size_message_shown"]
            },
            {
                "name": "test_invalid_file_type_rejection",
                "input": "document.txt (1MB)",
                "expected": "validation_error", 
                "assertions": ["error_code == 'INVALID_FILE_TYPE'", "allowed_types_message_shown"]
            },
            {
                "name": "test_corrupted_pdf_handling",
                "input": "corrupted.pdf (1MB)",
                "expected": "validation_error",
                "assertions": ["error_code == 'CORRUPTED_FILE'", "retry_message_shown"]
            }
        ]
    },
    "test_state_machine_transitions": {
        "description": "Verify application state transitions",
        "test_cases": [
            {
                "name": "test_draft_to_submitted_transition",
                "initial_state": "DRAFT",
                "action": "submit_form_with_valid_data",
                "expected_state": "FORM_SUBMITTED",
                "assertions": ["state_changed", "timestamp_updated", "progress_increased"]
            },
            {
                "name": "test_invalid_state_transition",
                "initial_state": "DRAFT", 
                "action": "make_decision",
                "expected": "InvalidStateTransitionError",
                "assertions": ["exception_raised", "state_unchanged", "error_logged"]
            },
            {
                "name": "test_graceful_failure_state",
                "initial_state": "PROCESSING",
                "action": "partial_processing_failure",
                "expected_state": "NEEDS_REVIEW",
                "assertions": ["partial_results_saved", "user_notified", "retry_available"]
            }
        ]
    }
}

# tests/unit/test_ai_services.py
AI_SERVICE_TESTS = {
    "test_ocr_service": {
        "test_cases": [
            {
                "name": "test_clear_bank_statement_extraction",
                "input": "clear_bank_statement.pdf",
                "expected": {
                    "confidence": "> 0.9",
                    "extracted_fields": ["account_number", "balance", "transactions"],
                    "processing_time": "< 30 seconds"
                }
            },
            {
                "name": "test_poor_quality_document",
                "input": "blurry_document.jpg", 
                "expected": {
                    "confidence": "< 0.7",
                    "partial_extraction": True,
                    "needs_manual_review": True
                }
            }
        ]
    },
    "test_multimodal_service": {
        "test_cases": [
            {
                "name": "test_structured_data_extraction",
                "input": "bank_statement.pdf",
                "expected": {
                    "monthly_income": "numeric_value",
                    "account_balance": "numeric_value", 
                    "confidence": "float_between_0_and_1"
                }
            },
            {
                "name": "test_model_unavailable_fallback",
                "setup": "mock_ollama_unavailable",
                "input": "any_document.pdf",
                "expected": {
                    "fallback_response": True,
                    "synthetic_data": True,
                    "processing_continues": True
                }
            }
        ]
    }
}
```

#### **Integration Test Specifications**
```python
# tests/integration/test_workflow_integration.py
INTEGRATION_TEST_CASES = {
    "test_complete_application_workflow": {
        "description": "Test end-to-end application processing",
        "steps": [
            {
                "action": "authenticate_user",
                "endpoint": "POST /auth/login",
                "data": {"username": "testuser1", "password": "password123"},
                "assertions": ["jwt_token_received", "user_authenticated"]
            },
            {
                "action": "create_application",
                "endpoint": "POST /workflow/start-application", 
                "data": {
                    "full_name": "Ahmed Test User",
                    "emirates_id": "784-1985-9876543-2",
                    "phone": "+971501234567",
                    "email": "ahmed@test.com"
                },
                "assertions": ["application_id_returned", "status_form_submitted"]
            },
            {
                "action": "upload_documents",
                "endpoint": "POST /workflow/upload-documents/{application_id}",
                "files": ["test_bank_statement.pdf", "test_emirates_id.jpg"],
                "assertions": ["documents_uploaded", "processing_started", "job_queued"]
            },
            {
                "action": "wait_for_processing",
                "poll_endpoint": "GET /workflow/status/{application_id}",
                "wait_for": "status != 'processing'",
                "timeout": "120 seconds",
                "assertions": ["processing_completed", "decision_made"]
            },
            {
                "action": "verify_results",
                "endpoint": "GET /applications/{application_id}/results",
                "assertions": [
                    "decision_in_['approved', 'rejected', 'needs_review']",
                    "confidence_score_present",
                    "reasoning_provided",
                    "next_steps_defined"
                ]
            }
        ]
    },
    "test_graceful_failure_workflow": {
        "description": "Test system behavior during partial failures",
        "setup": "configure_partial_ai_failure",
        "steps": [
            "create_application_normally",
            "upload_documents_normally", 
            "simulate_ocr_failure_on_bank_statement",
            "verify_emirates_id_processes_successfully",
            "verify_decision_made_with_partial_data",
            "verify_needs_review_status_set",
            "verify_user_informed_of_partial_success"
        ]
    }
}

# tests/integration/test_api_performance.py
PERFORMANCE_TEST_CASES = {
    "test_concurrent_document_processing": {
        "description": "Test system under concurrent load",
        "setup": {
            "concurrent_users": 3,
            "documents_per_user": 2,
            "total_processing_jobs": 6
        },
        "assertions": [
            "all_jobs_complete_within_10_minutes",
            "no_job_failures_due_to_resource_contention", 
            "queue_management_working",
            "response_times_acceptable"
        ]
    },
    "test_large_document_processing": {
        "description": "Test processing of maximum size documents",
        "test_data": "50MB_bank_statement.pdf",
        "assertions": [
            "processing_completes_within_5_minutes",
            "memory_usage_stays_under_limits",
            "no_timeout_errors",
            "results_quality_maintained"
        ]
    }
}
```

#### **End-to-End Test Specifications**
```python
# tests/e2e/test_user_journey.py  
E2E_TEST_SCENARIOS = {
    "scenario_successful_application": {
        "description": "Complete user journey from login to approval",
        "user_persona": "Eligible applicant with clear documents",
        "steps": [
            "navigate_to_application",
            "login_with_test_credentials", 
            "fill_application_form_completely",
            "upload_valid_documents",
            "wait_for_processing_completion",
            "verify_approval_decision",
            "verify_next_steps_displayed"
        ],
        "success_criteria": [
            "total_time < 5 minutes",
            "no_user_errors_encountered",
            "clear_decision_received",
            "next_steps_actionable"
        ]
    },
    "scenario_document_resubmission": {
        "description": "User recovers from initial document upload failure",
        "user_persona": "User with initially poor quality documents",
        "steps": [
            "complete_initial_application_flow",
            "receive_processing_failure_notification",
            "understand_error_message",
            "upload_replacement_documents", 
            "receive_successful_processing",
            "get_final_decision"
        ],
        "success_criteria": [
            "clear_error_explanation_provided",
            "easy_resubmission_process",
            "no_data_loss_during_retry",
            "successful_recovery_completion"
        ]
    }
}
```

### **Test Data & Fixtures**
```python
# Test data generation specifications
TEST_DATA_REQUIREMENTS = {
    "synthetic_documents": {
        "bank_statements": {
            "count": 20,
            "variations": [
                "high_income_approved",
                "low_income_rejected", 
                "borderline_income_review",
                "missing_data_fields",
                "poor_image_quality"
            ],
            "format": "PDF with realistic UAE bank statement layout"
        },
        "emirates_ids": {
            "count": 20,
            "variations": [
                "clear_scan_high_quality",
                "photo_medium_quality",
                "expired_document",
                "damaged_document",
                "non_standard_format"
            ],
            "formats": ["PDF", "JPG", "PNG"]
        }
    },
    "test_users": {
        "count": 10,
        "profiles": [
            {"username": "user1", "scenario": "always_approved"},
            {"username": "user2", "scenario": "always_rejected"},
            {"username": "user3", "scenario": "needs_review"},
            {"username": "admin", "scenario": "system_admin"},
            {"username": "testbot", "scenario": "automated_testing"}
        ]
    }
}
```

---

## 📊 **LOGGING, MONITORING & OBSERVABILITY**

### **Structured Logging Configuration**
```python
# Comprehensive logging strategy
LOGGING_CONFIGURATION = {
    "format": "json_structured",
    "level_hierarchy": {
        "production": "WARNING",
        "development": "DEBUG", 
        "testing": "INFO"
    },
    "log_structure": {
        "timestamp": "ISO 8601 format",
        "level": "DEBUG|INFO|WARNING|ERROR|CRITICAL",
        "service": "service_name",
        "module": "python_module_name", 
        "function": "function_name",
        "user_id": "uuid (if available)",
        "application_id": "uuid (if applicable)",
        "request_id": "uuid (for tracing)",
        "duration_ms": "integer (for timed operations)",
        "message": "human_readable_message",
        "extra": "context_specific_data"
    },
    "log_files": {
        "app.log": "All application logs",
        "worker.log": "Background worker logs", 
        "error.log": "ERROR and CRITICAL only",
        "access.log": "API request/response logs",
        "security.log": "Authentication and authorization logs"
    }
}

# Example structured log entries
SAMPLE_LOG_ENTRIES = {
    "user_authentication": {
        "timestamp": "2024-12-19T14:30:22.123Z",
        "level": "INFO",
        "service": "user_management",
        "module": "auth_flow",
        "function": "authenticate_user",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "request_id": "req_789xyz",
        "duration_ms": 45,
        "message": "User authentication successful",
        "extra": {
            "auth_method": "jwt",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0..."
        }
    },
    "document_processing": {
        "timestamp": "2024-12-19T14:31:15.456Z",
        "level": "INFO",
        "service": "document_processing",
        "module": "ocr_service", 
        "function": "extract_text",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "application_id": "app_456abc",
        "request_id": "req_789xyz",
        "duration_ms": 23450,
        "message": "OCR processing completed successfully",
        "extra": {
            "document_type": "bank_statement",
            "file_size": 2097152,
            "confidence_score": 0.95,
            "text_length": 1205,
            "processing_engine": "easyocr"
        }
    },
    "error_with_context": {
        "timestamp": "2024-12-19T14:32:01.789Z",
        "level": "ERROR", 
        "service": "document_processing",
        "module": "multimodal_service",
        "function": "analyze_document",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "application_id": "app_456abc",
        "request_id": "req_789xyz",
        "duration_ms": 5000,
        "message": "Multimodal analysis failed due to model timeout",
        "extra": {
            "error_type": "ModelTimeoutError",
            "model_name": "moondream:1.8b",
            "timeout_seconds": 300,
            "retry_attempt": 1,
            "fallback_used": True,
            "stack_trace": "..."
        }
    }
}
```

### **Health Monitoring Specifications**
```python
# Comprehensive health check requirements
HEALTH_MONITORING = {
    "system_health_checks": {
        "database_connectivity": {
            "check": "PostgreSQL connection and query execution",
            "healthy_criteria": "Connection successful and query < 100ms",
            "unhealthy_actions": ["Log error", "Return service unavailable", "Alert admin"]
        },
        "redis_connectivity": {
            "check": "Redis ping and basic operations", 
            "healthy_criteria": "Ping successful and operations < 50ms",
            "unhealthy_actions": ["Disable caching", "Use direct processing", "Alert admin"]
        },
        "ollama_model_availability": {
            "check": "All required models loaded and responsive",
            "healthy_criteria": "All models respond to test inference < 30s",
            "unhealthy_actions": ["Enable mock mode", "Queue requests", "Alert admin"]
        },
        "celery_workers": {
            "check": "Worker processes active and accepting tasks",
            "healthy_criteria": "At least 1 worker active, queue depth < 10",
            "unhealthy_actions": ["Restart workers", "Queue management", "Alert admin"]
        },
        "file_system": {
            "check": "Disk space and write permissions",
            "healthy_criteria": "< 80% disk usage, write test successful",
            "unhealthy_actions": ["Cleanup old files", "Prevent new uploads", "Alert admin"]
        }
    },
    "application_metrics": {
        "processing_performance": {
            "total_applications_processed": "counter",
            "average_processing_time": "histogram", 
            "processing_success_rate": "percentage",
            "processing_failure_rate": "percentage",
            "queue_depth": "gauge"
        },
        "resource_utilization": {
            "cpu_usage_percentage": "gauge",
            "memory_usage_mb": "gauge", 
            "disk_usage_percentage": "gauge",
            "active_connections": "gauge"
        },
        "business_metrics": {
            "applications_per_hour": "rate",
            "approval_rate": "percentage",
            "manual_review_rate": "percentage",
            "user_satisfaction_score": "gauge"
        }
    },
    "alerting_thresholds": {
        "critical_alerts": {
            "database_down": "immediate",
            "all_workers_down": "immediate",
            "disk_space_95_percent": "immediate"
        },
        "warning_alerts": {
            "processing_time_over_2_minutes": "5 minutes",
            "error_rate_over_10_percent": "10 minutes",
            "queue_depth_over_20": "15 minutes"
        }
    }
}
```

---

## 🚀 **DEPLOYMENT & INFRASTRUCTURE**

### **Container Architecture & Deployment Strategy**
```yaml
# Complete Docker Compose specification
version: '3.8'

services:
  # Main Application
  fastapi-app:
    build: 
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://admin:${POSTGRES_PASSWORD}@postgres:5432/social_security_ai
      - REDIS_URL=redis://redis:6379
      - OLLAMA_URL=http://ollama:11434
      - QDRANT_URL=http://qdrant:6333
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    networks:
      - social-security-net
    depends_on:
      - postgres
      - redis
      - qdrant
      - ollama
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Background Workers
  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://admin:${POSTGRES_PASSWORD}@postgres:5432/social_security_ai
      - REDIS_URL=redis://redis:6379
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    networks:
      - social-security-net
    depends_on:
      - postgres
      - redis
      - ollama
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  # Frontend Dashboard
  streamlit-frontend:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["streamlit", "run", "frontend/dashboard_app.py", "--server.port=8005", "--server.address=0.0.0.0"]
    ports:
      - "8005:8005"
    environment:
      - API_BASE_URL=http://fastapi-app:8000
      - STREAMLIT_SERVER_HEADLESS=true
    networks:
      - social-security-net
    depends_on:
      - fastapi-app

  # AI Model Server
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    networks:
      - social-security-net
    environment:
      - OLLAMA_HOST=0.0.0.0
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G

  # PostgreSQL Database
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=social_security_ai
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --locale=C
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - social-security-net
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  # Redis Cache & Message Broker
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - social-security-net

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - social-security-net

networks:
  social-security-net:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  ollama_models:
```

### **Production Environment Configuration**
```bash
# .env.production
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING

# Security Configuration
JWT_SECRET_KEY=your-super-secure-production-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Configuration
POSTGRES_PASSWORD=secure-production-password-min-16-chars
DATABASE_URL=postgresql://admin:${POSTGRES_PASSWORD}@postgres:5432/social_security_ai
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=optional-redis-password

# AI Configuration
OLLAMA_URL=http://ollama:11434
OLLAMA_REQUEST_TIMEOUT=300
OLLAMA_MAX_RETRIES=3

# File Upload Configuration
MAX_FILE_SIZE=52428800
ALLOWED_EXTENSIONS=pdf,jpg,jpeg,png
UPLOAD_DIR=/app/uploads

# Processing Configuration
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
CELERY_WORKER_CONCURRENCY=2
CELERY_TASK_TIME_LIMIT=600
CELERY_TASK_SOFT_TIME_LIMIT=300

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30

# Business Rules Configuration
INCOME_THRESHOLD_AED=4000
BALANCE_THRESHOLD_AED=1500
CONFIDENCE_THRESHOLD=0.7
AUTO_APPROVAL_THRESHOLD=0.8
```

### **Installation & Setup Guide**
```bash
#!/bin/bash
# Complete system installation script

# Step 1: Prerequisites check
echo "Checking prerequisites..."
docker --version || { echo "Docker not installed"; exit 1; }
docker-compose --version || { echo "Docker Compose not installed"; exit 1; }

# Step 2: Clone and setup project
echo "Setting up project..."
git clone <repository-url>
cd social_security_ai

# Step 3: Environment configuration
echo "Configuring environment..."
cp .env.example .env
echo "Please edit .env file with your specific configuration"
read -p "Press enter when .env is configured..."

# Step 4: Create necessary directories
echo "Creating directories..."
mkdir -p uploads logs scripts/backups
chmod 755 uploads logs

# Step 5: Build and start infrastructure services
echo "Starting infrastructure services..."
docker-compose up -d postgres redis qdrant

# Wait for databases to be ready
echo "Waiting for databases to initialize..."
sleep 30

# Step 6: Initialize database
echo "Initializing database..."
python scripts/init_db.py
python scripts/seed_users.py

# Step 7: Start Ollama and download models
echo "Starting AI model server..."
docker-compose up -d ollama
echo "Waiting for Ollama to start..."
sleep 60

echo "Downloading AI models (this may take several minutes)..."
docker exec -it $(docker-compose ps -q ollama) ollama pull moondream:1.8b
docker exec -it $(docker-compose ps -q ollama) ollama pull qwen2:1.5b
docker exec -it $(docker-compose ps -q ollama) ollama pull nomic-embed-text

# Step 8: Generate test data
echo "Generating synthetic test data..."
python scripts/generate_test_data.py

# Step 9: Start application services
echo "Starting application services..."
docker-compose up --build -d

# Step 10: Health check
echo "Performing health check..."
sleep 30
curl -f http://localhost:8000/health || { echo "Health check failed"; exit 1; }

echo "Installation complete!"
echo "Access the application:"
echo "- Dashboard: http://localhost:8005"
echo "- API Documentation: http://localhost:8000/docs"
echo "- Health Check: http://localhost:8000/health"
echo ""
echo "Test credentials:"
echo "- Username: user1, Password: password123"
echo "- Username: user2, Password: password123"
```

---

## 📝 **DEVELOPMENT GUIDELINES & STANDARDS**

### **Code Organization Principles**
```python
# Flow-based architecture guidelines
ARCHITECTURE_PRINCIPLES = {
    "flow_based_organization": {
        "principle": "Organize code by business workflows, not technical layers",
        "structure": "user_management/, application_flow/, document_processing/, decision_making/",
        "benefits": ["Clear business logic separation", "Easy to understand workflows", "Natural testing boundaries"]
    },
    "single_responsibility": {
        "principle": "Each module handles one primary business concern",
        "implementation": "Separate services for auth, documents, decisions",
        "benefits": ["Easy to test", "Clear ownership", "Minimal coupling"]
    },
    "graceful_degradation": {
        "principle": "System continues operating with partial failures",
        "implementation": "Try-catch all external dependencies, fallback responses",
        "benefits": ["Better user experience", "Higher availability", "Predictable behavior"]
    }
}

# Coding standards and conventions
CODING_STANDARDS = {
    "python_style": {
        "formatter": "black",
        "line_length": 88,
        "imports": "isort with black profile",
        "docstrings": "Google style",
        "type_hints": "Required for all public functions"
    },
    "naming_conventions": {
        "functions": "snake_case",
        "classes": "PascalCase", 
        "constants": "UPPER_SNAKE_CASE",
        "files": "snake_case",
        "directories": "snake_case"
    },
    "error_handling": {
        "exceptions": "Use custom exception classes", 
        "logging": "Log all errors with context",
        "user_messages": "Clear, actionable error messages",
        "recovery": "Provide retry mechanisms where possible"
    }
}
```

### **API Design Guidelines**
```python
# Consistent API design patterns
API_DESIGN_PRINCIPLES = {
    "workflow_based_endpoints": {
        "pattern": "/workflow/{action}",
        "examples": [
            "POST /workflow/start-application",
            "POST /workflow/upload-documents/{id}",
            "GET /workflow/status/{id}"
        ],
        "rationale": "Matches user mental model of processes"
    },
    "response_consistency": {
        "success_format": {
            "status": "success",
            "data": {},
            "message": "Human readable message",
            "metadata": {"timestamp": "ISO8601", "request_id": "uuid"}
        },
        "error_format": {
            "status": "error", 
            "error": {"code": "ERROR_CODE", "message": "User message"},
            "details": {"field_errors": {}, "context": {}},
            "metadata": {"timestamp": "ISO8601", "request_id": "uuid"}
        }
    },
    "status_codes": {
        "200": "Successful operation with data",
        "201": "Resource created successfully",
        "202": "Accepted for processing (async operations)",
        "400": "Client error (validation, malformed request)",
        "401": "Authentication required",
        "403": "Forbidden (authorized but no permission)",
        "404": "Resource not found",
        "409": "Conflict (duplicate resource, invalid state)",
        "422": "Validation failed",
        "500": "Internal server error",
        "503": "Service unavailable (dependencies down)"
    }
}
```

### **Database Design Guidelines**
```sql
-- Database schema design principles
-- Moderately normalized design with strategic denormalization

-- Users table (authentication)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Indexes for performance
    INDEX idx_users_username (username),
    INDEX idx_users_email (email)
);

-- Applications table (main entity)
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Form data
    full_name VARCHAR(255) NOT NULL,
    emirates_id VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    
    -- State management
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    progress INTEGER DEFAULT 0,
    
    -- Document references (denormalized for performance)
    bank_statement_id UUID,
    emirates_id_doc_id UUID,
    
    -- Processing results (denormalized)
    monthly_income DECIMAL(10,2),
    account_balance DECIMAL(10,2),
    eligibility_score DECIMAL(3,2),
    
    -- Decision results
    decision VARCHAR(20), -- 'approved', 'rejected', 'needs_review'
    decision_confidence DECIMAL(3,2),
    decision_reasoning TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    submitted_at TIMESTAMP,
    processed_at TIMESTAMP,
    decision_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_applications_user (user_id),
    INDEX idx_applications_status (status),
    INDEX idx_applications_created (created_at)
);

-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- File metadata
    document_type VARCHAR(50) NOT NULL, -- 'bank_statement', 'emirates_id'
    original_filename VARCHAR(255),
    file_path TEXT NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    
    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'uploaded',
    ocr_confidence DECIMAL(3,2),
    extracted_text TEXT,
    structured_data JSONB,
    
    -- Timestamps
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_documents_application (application_id),
    INDEX idx_documents_type (document_type),
    INDEX idx_documents_status (processing_status)
);

-- Workflow states table (detailed state tracking)
CREATE TABLE workflow_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    
    -- State information
    current_state VARCHAR(50) NOT NULL,
    previous_state VARCHAR(50),
    state_data JSONB,
    
    -- Processing information
    step_name VARCHAR(100),
    step_status VARCHAR(50),
    step_message TEXT,
    processing_time_ms INTEGER,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_workflow_application (application_id),
    INDEX idx_workflow_state (current_state),
    INDEX idx_workflow_created (created_at)
);
```

---

## 🎨 **UI/UX DESIGN SPECIFICATIONS**

### **Design System & Component Library**
```python
# Streamlit component specifications
DESIGN_SYSTEM = {
    "color_palette": {
        "primary": "#1f77b4",      # Professional blue
        "secondary": "#ff7f0e",    # Warning orange
        "success": "#2ca02c",      # Success green
        "danger": "#d62728",       # Error red
        "warning": "#ff7f0e",      # Warning orange
        "info": "#17a2b8",         # Info cyan
        "light": "#f8f9fa",        # Light gray
        "dark": "#343a40"          # Dark gray
    },
    "typography": {
        "headings": "Inter, sans-serif",
        "body": "Inter, sans-serif", 
        "code": "JetBrains Mono, monospace",
        "sizes": {
            "h1": "2rem",
            "h2": "1.5rem",
            "h3": "1.25rem",
            "body": "1rem",
            "small": "0.875rem"
        }
    },
    "spacing": {
        "xs": "0.25rem",
        "sm": "0.5rem",
        "md": "1rem",
        "lg": "1.5rem", 
        "xl": "2rem",
        "xxl": "3rem"
    },
    "component_styling": {
        "panels": {
            "background": "white",
            "border": "1px solid #dee2e6",
            "border_radius": "0.375rem",
            "padding": "1rem",
            "shadow": "0 1px 3px rgba(0,0,0,0.1)"
        },
        "status_indicators": {
            "completed": {"color": "#2ca02c", "icon": "✅"},
            "in_progress": {"color": "#17a2b8", "icon": "◐"},
            "pending": {"color": "#6c757d", "icon": "⏳"},
            "failed": {"color": "#d62728", "icon": "❌"},
            "needs_review": {"color": "#ff7f0e", "icon": "👀"}
        }
    }
}

# Responsive design breakpoints
RESPONSIVE_DESIGN = {
    "breakpoints": {
        "mobile": "< 768px",
        "tablet": "768px - 1199px", 
        "desktop": "> 1200px"
    },
    "layouts": {
        "mobile": {
            "structure": "Single column accordion",
            "panels": "Collapsible sections",
            "navigation": "Hamburger menu"
        },
        "tablet": {
            "structure": "Two column layout",
            "panels": "Side-by-side with scrolling",
            "navigation": "Top navigation bar"
        },
        "desktop": {
            "structure": "Three column dashboard",
            "panels": "Fixed width panels",
            "navigation": "Persistent sidebar"
        }
    }
}
```

### **Dashboard Component Specifications**
```python
# Detailed component specifications for Streamlit implementation
DASHBOARD_COMPONENTS = {
    "application_panel": {
        "width": "33%",
        "height": "600px",
        "components": [
            {
                "type": "form",
                "fields": [
                    {"name": "full_name", "type": "text_input", "required": True},
                    {"name": "emirates_id", "type": "text_input", "required": True, "pattern": "784-[0-9]{4}-[0-9]{7}-[0-9]"},
                    {"name": "phone", "type": "text_input", "required": True},
                    {"name": "email", "type": "text_input", "required": True}
                ]
            },
            {
                "type": "button_group",
                "buttons": [
                    {"label": "Save Draft", "style": "secondary", "action": "save_draft"},
                    {"label": "Submit Application", "style": "primary", "action": "submit_form"}
                ]
            }
        ]
    },
    "document_panel": {
        "width": "33%",
        "height": "600px", 
        "components": [
            {
                "type": "file_uploader",
                "multiple": False,
                "accepted_types": ["pdf", "jpg", "png"],
                "max_file_size": "50MB",
                "label": "Bank Statement"
            },
            {
                "type": "file_uploader",
                "multiple": False,
                "accepted_types": ["pdf", "jpg", "png"],
                "max_file_size": "50MB",
                "label": "Emirates ID"
            },
            {
                "type": "document_preview",
                "show_metadata": True,
                "show_processing_status": True
            }
        ]
    },
    "status_panel": {
        "width": "34%",
        "height": "600px",
        "components": [
            {
                "type": "progress_bar",
                "animated": True,
                "show_percentage": True,
                "color_coding": True
            },
            {
                "type": "status_timeline",
                "show_timestamps": True,
                "show_duration": True,
                "expandable_details": True
            },
            {
                "type": "metrics_display",
                "metrics": ["confidence_score", "processing_time", "estimated_completion"]
            }
        ]
    },
    "results_panel": {
        "width": "100%",
        "height": "200px",
        "components": [
            {
                "type": "decision_display",
                "show_reasoning": True,
                "show_confidence": True,
                "expandable_details": True
            },
            {
                "type": "action_buttons",
                "buttons": ["download_certificate", "contact_support", "start_new_application"]
            }
        ]
    }
}
```

---

## 🔐 **SECURITY & COMPLIANCE SPECIFICATIONS**

### **Security Requirements & Implementation**
```python
SECURITY_REQUIREMENTS = {
    "authentication": {
        "method": "JWT Bearer tokens",
        "token_expiration": "24 hours",
        "password_requirements": {
            "min_length": 8,
            "require_uppercase": False,
            "require_lowercase": False,
            "require_numbers": False,
            "require_special_chars": False
        },
        "rate_limiting": {
            "login_attempts": "5 per 15 minutes per IP",
            "api_requests": "100 per minute per user"
        }
    },
    "file_upload_security": {
        "size_limits": "50MB maximum",
        "type_validation": "Check file headers and extensions",
        "path_traversal_prevention": "Sanitize all file paths",
        "virus_scanning": "Not implemented (future enhancement)",
        "content_validation": "Basic PDF/image format validation"
    },
    "data_protection": {
        "encryption_at_rest": "PostgreSQL transparent data encryption",
        "encryption_in_transit": "TLS 1.3 for all connections",
        "sensitive_data_handling": "No PII in logs, secure deletion",
        "session_management": "Secure JWT tokens with proper expiration"
    },
    "api_security": {
        "input_validation": "Pydantic models for all inputs",
        "output_sanitization": "No sensitive data in error messages", 
        "cors_policy": "Restrict to known origins",
        "security_headers": "Standard security headers in responses"
    }
}

# Implementation guidelines for secure coding
SECURE_CODING_PRACTICES = {
    "input_validation": {
        "principle": "Validate all inputs at API boundary",
        "implementation": "Pydantic models with custom validators",
        "example": """
        class ApplicationRequest(BaseModel):
            emirates_id: str = Field(..., regex=r'^784-[0-9]{4}-[0-9]{7}-[0-9]$')
            email: EmailStr
            phone: str = Field(..., regex=r'^(\+971|05)[0-9]{8,9}$')
        """
    },
    "error_handling": {
        "principle": "Never expose system internals in error messages",
        "implementation": "Generic error messages with detailed logging",
        "example": """
        try:
            result = process_document(file)
        except Exception as e:
            logger.error(f"Document processing failed: {e}", extra={"user_id": user_id})
            raise HTTPException(500, "Document processing failed. Please try again.")
        """
    },
    "file_handling": {
        "principle": "Treat all uploaded files as potentially malicious",
        "implementation": "Validation, sandboxing, and secure storage",
        "example": """
        def save_uploaded_file(file: UploadFile, application_id: str):
            # Validate file type and size
            validate_file_security(file)
            # Generate secure path
            secure_path = generate_secure_path(application_id, file.filename)
            # Save with restricted permissions
            save_file_securely(file, secure_path)
        """
    }
}
```

---

This comprehensive master specification document provides **complete technical requirements** for generating the entire Social Security AI Workflow Automation System. It covers every aspect from architecture to implementation details, ensuring that any AI system (like Claude) can generate a production-ready, sophisticated government application processing system with graceful failure handling, detailed status tracking, and enterprise-grade reliability.

The document serves as a **complete blueprint** for building:
- ✅ **Production-ready codebase** with all files and configurations
- ✅ **Sophisticated dashboard UI** with three-panel layout  
- ✅ **Flow-based architecture** with detailed state management
- ✅ **Graceful failure handling** with partial data processing
- ✅ **Comprehensive testing suite** with unit, integration, and E2E tests
- ✅ **Complete deployment pipeline** with Docker containers
- ✅ **Enterprise security** and compliance features
- ✅ **Detailed documentation** and development guidelines

This specification enables rapid development of a **complex, enterprise-grade AI system** while maintaining code quality, security standards, and user experience excellence.