# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Social Security AI Workflow Automation System** - a complete enterprise-grade AI-powered government workflow with 58+ API endpoints across 11 modules. The system transforms traditional 5-20 day manual processes into 2-minute AI-driven workflows with 99% automation.

**New in v4.3.0**: Comprehensive document management system with full CRUD operations, advanced session persistence, and separated submission/processing workflows. Features include document preview, status tracking, and complete state recovery across page refreshes.

### Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Streamlit Dashboard (8005)                 │
│             Real-Time Three-Panel Interface                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP API Calls
┌──────────────────────▼──────────────────────────────────────┐
│                FastAPI Application (8000)                  │
│  ├── user_management/     - Authentication flows           │
│  ├── application_flow/    - Application lifecycle          │
│  ├── document_processing/ - OCR & analysis                 │
│  ├── decision_making/     - AI eligibility engine          │
│  └── workers/             - Background processing          │
└──────────────────────┬──────────────────────────────────────┘
                       │ AI Model Inference
┌──────────────────────▼──────────────────────────────────────┐
│                Ollama AI Server (11434)                    │
│  ├── moondream:1.8b  - Document analysis                   │
│  ├── qwen2:1.5b      - Decision reasoning                  │
│  └── nomic-embed-text - Embeddings                         │
└──────────────────────┬──────────────────────────────────────┘
                       │ Data Storage
┌──────────────────────▼──────────────────────────────────────┐
│  PostgreSQL + Redis + Qdrant + Local Files                │
└─────────────────────────────────────────────────────────────┘
```

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Database Operations
```bash
# Initialize database
python -c "from app.shared.database import init_db; init_db()"

# Generate test data
python scripts/setup/generate_test_data.py
```

### Running Services

#### Local Development (Recommended)
```bash
# Start infrastructure services with Docker
docker-compose up -d postgres redis qdrant ollama

# Start FastAPI backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start Celery workers (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2

# Start Streamlit frontend (separate terminal)
streamlit run frontend/dashboard_app.py --server.port=8005 --server.address=0.0.0.0
```

#### Complete Docker Deployment
```bash
# Start all services
docker-compose up -d

# Download AI models
docker exec $(docker-compose ps -q ollama) ollama pull moondream:1.8b
docker exec $(docker-compose ps -q ollama) ollama pull qwen2:1.5b
docker exec $(docker-compose ps -q ollama) ollama pull nomic-embed-text
```

#### Quick Start Script
```bash
# Start all services automatically
./scripts/start_all_services.sh

# Stop all services
./scripts/stop_all_services.sh
```

### Testing

#### Run Tests
```bash
# All tests
pytest

# Specific test categories
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/api/            # API tests
pytest tests/system/         # System tests

# With coverage
pytest --cov=app tests/

# Quick API test
python tests/quick_api_test.py

# Complete system test
python tests/demo_workflow_test.py
```

#### Test Files by Category
- **Unit Tests**: `tests/unit/` - Individual component tests
- **Integration Tests**: `tests/integration/` - Cross-service integration
- **API Tests**: `tests/api/` - Complete API endpoint testing
- **System Tests**: `tests/system/` - End-to-end validation

### Code Quality
```bash
# Format code
black .

# Sort imports
isort .

# Run linting (if configured)
# No specific linter configured in project
```

## System Architecture Details

### Core Modules
- **`app/user_management/`** - JWT authentication, user profiles, role-based access
- **`app/document_processing/`** - OCR service, multimodal AI analysis, file management
- **`app/decision_making/`** - ReAct reasoning framework, eligibility assessment
- **`app/application_flow/`** - 12-state workflow management
- **`app/workers/`** - Celery background processing
- **`app/shared/`** - Database, logging, utilities
- **`app/api/`** - 11 router modules with 58 endpoints

### Frontend Structure
- **`frontend/dashboard_app.py`** - Main Streamlit application with single-application interface
- **`frontend/components/`** - Reusable UI components
  - **`navigation.py`** - Simplified single-application navigation (v4.2.0)
  - **`application_panel.py`** - Enhanced form management with context-aware actions
  - **`document_management.py`** - Comprehensive document CRUD operations (new in v4.3.0)
  - **`auth_component.py`** - Authentication with session persistence
- **`frontend/utils/`** - API client and utilities
  - **`auth_cookies.py`** - Advanced session persistence with document metadata (v4.3.0)
  - **`dashboard_state.py`** - Enhanced state management with document recovery
  - **`api_client.py`** - Extended with document management endpoints (v4.3.0)

### Key Technologies
- **Backend**: FastAPI + SQLAlchemy + Pydantic
- **Frontend**: Streamlit with real-time updates
- **AI**: Ollama (moondream, qwen2, nomic-embed-text models)
- **Storage**: PostgreSQL + Redis + Qdrant vector DB
- **Processing**: Celery + Redis message broker
- **OCR**: EasyOCR (currently disabled for Python 3.13 compatibility)

## Business Logic

### Workflow States (12-state pipeline)
1. DRAFT → 2. FORM_SUBMITTED → 3. DOCUMENTS_UPLOADED → 4. SCANNING_DOCUMENTS → 5. OCR_COMPLETED → 6. ANALYZING_INCOME → 7. ANALYZING_IDENTITY → 8. ANALYSIS_COMPLETED → 9. MAKING_DECISION → 10. DECISION_COMPLETED → 11. APPROVED/REJECTED → 12. NEEDS_REVIEW

### Document Management (v4.3.0)
- **Complete CRUD Operations**: Upload, view, edit, replace, delete, and reset documents
- **Separated Workflows**: Submit documents first, then process separately
- **Session Persistence**: Documents survive page refresh and browser restart
- **Status Tracking**: uploaded → submitted → processing → processed
- **Smart Preview**: View PDFs inline, download images with preview
- **One Document Per Type**: Single bank statement and single Emirates ID per application

### Document Types
- **Bank Statement**: PDF format, 50MB max
- **Emirates ID**: Image formats (PNG, JPG, JPEG), 50MB max

### AI Decision Criteria
- Income threshold: 4000 AED
- Balance threshold: 1500 AED
- Confidence threshold: 0.7 (manual review)
- Auto-approval threshold: 0.8

## API Endpoints

### Core Modules (58 endpoints)
- **Authentication** (7): `/auth/` - register, login, profile, logout
- **Document Upload** (4): `/documents/` - upload, status, types
- **Document Management** (8): `/document-management/` - CRUD operations
- **Workflow** (3): `/workflow/` - start, status, process
- **Application** (4): `/applications/` - results, updates
- **AI Analysis** (4): `/analysis/` - document analysis
- **OCR Processing** (5): `/ocr/` - text extraction
- **Decision Making** (5): `/decisions/` - AI decisions
- **Chatbot** (6): `/chatbot/` - AI assistance
- **User Management** (8): `/user/` - profile, admin
- **Health** (3): `/health/` - system monitoring
- **Root** (1): `/` - API info

### Authentication Required
- 45 endpoints require `Authorization: Bearer <token>`
- 13 public endpoints (health, registration, login)

## Environment Configuration

### Required Environment Variables
```bash
# Security
JWT_SECRET_KEY=your-super-secure-development-key-min-32-chars-long

# Database
DATABASE_URL=postgresql://admin:postgres123@postgres:5432/social_security_ai

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# AI Services
OLLAMA_URL=http://ollama:11434
QDRANT_URL=http://qdrant:6333

# File Processing
MAX_FILE_SIZE=52428800  # 50MB
UPLOAD_DIR=./uploads
```

## Access Points

### Service URLs
- **Frontend Dashboard**: http://localhost:8005
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Test Credentials
- Username: `user1` / Password: `password123`
- Username: `user2` / Password: `password123`

## Production Deployment

The system is production-ready with:
- Docker containerization
- Health monitoring
- Structured logging
- Error handling
- Security middleware
- Background processing
- Real-time status updates

Use `scripts/start_all_services.sh` for complete system deployment or docker-compose for containerized deployment.