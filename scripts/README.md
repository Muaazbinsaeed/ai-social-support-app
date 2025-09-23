# Scripts Directory Documentation

This directory contains organized scripts for managing the AI Social Support App system deployment, testing, and maintenance.

## Directory Structure

```
scripts/
├── database/           # Database management and migration scripts
├── deployment/         # Docker deployment and container management
├── monitoring/         # Health checks and system validation
├── setup/             # System initialization and data generation
├── testing/           # Test execution and validation scripts
├── start_all_services.sh          # Complete Docker deployment
├── start_all_services_local.sh    # Local development deployment
└── stop_all_services.sh           # Stop all services
```

## Core Service Management Scripts

### 🚀 Service Startup Scripts

#### `start_all_services.sh`
**Purpose**: Complete Docker containerized deployment
**Usage**: `./scripts/start_all_services.sh`
**What it does**:
- Starts all infrastructure services (PostgreSQL, Redis, Qdrant, Ollama)
- Builds and deploys FastAPI backend in container
- Starts Celery workers in container
- Deploys Streamlit frontend in container
- Downloads required AI models (moondream:1.8b, qwen2:1.5b, nomic-embed-text)
- Provides health check validation

#### `start_all_services_local.sh` (Recommended for Development)
**Purpose**: Local development with hot reload
**Usage**: `./scripts/start_all_services_local.sh`
**What it does**:
- Starts infrastructure with Docker (PostgreSQL, Redis, Qdrant, Ollama)
- Runs FastAPI backend locally with `--reload` flag
- Starts Celery workers locally with virtualenv
- Runs Streamlit frontend locally with virtualenv
- Maintains PID files for process management (.fastapi.pid, .celery.pid, .streamlit.pid)
- Enables code hot-reloading for development

#### `stop_all_services.sh`
**Purpose**: Clean shutdown of all services
**Usage**: `./scripts/stop_all_services.sh`
**What it does**:
- Kills local processes using PID files
- Stops Docker containers gracefully
- Cleans up PID files
- Provides confirmation of service shutdown

## Directory-Specific Scripts

### 📊 Database Management (`database/`)
- **Purpose**: Database schema management, migrations, and data fixes
- **Key Scripts**:
  - `add_missing_columns.py` - Fixes missing database columns (common issue)
  - `add_updated_at_column.py` - Database migration for v4.6.0+ compatibility
  - `fix_missing_columns.py` - Comprehensive schema repair script
- **Usage**: Run when encountering "column does not exist" errors

### 🐳 Deployment Management (`deployment/`)
- **Purpose**: Docker containerization and production deployment
- **Key Scripts**:
  - Container health checks
  - Docker Compose management
  - Production deployment scripts
- **Usage**: For production and containerized deployments

### 🔍 System Monitoring (`monitoring/`)
- **Purpose**: Health checks, system validation, and performance monitoring
- **Key Scripts**:
  - Service health validation
  - API endpoint testing
  - System status reporting
- **Usage**: Verify system health and diagnose issues

### ⚙️ System Setup (`setup/`)
- **Purpose**: Initial system configuration and test data generation
- **Key Scripts**:
  - `generate_test_data.py` - Creates sample applications and documents
  - Database initialization
  - Environment configuration
- **Usage**: First-time setup and testing preparation

### 🧪 Testing Framework (`testing/`)
- **Purpose**: Automated testing, validation, and system verification
- **Key Scripts**:
  - `run_module1_tests.py` - User authentication module testing
  - API endpoint validation
  - End-to-end workflow testing
- **Usage**: Quality assurance and regression testing

## Common Usage Patterns

### 🚀 Quick Development Start
```bash
# Recommended for development
./scripts/start_all_services_local.sh

# Check services are running
curl http://localhost:8000/health
```

### 🔧 Database Issue Resolution
```bash
# If you see "column does not exist" errors
python scripts/database/fix_missing_columns.py

# Or specifically for updated_at column
python scripts/database/add_updated_at_column.py
```

### 🧪 Testing Workflow
```bash
# Quick API validation
python tests/quick_api_test.py

# Complete workflow demonstration
python tests/demo_workflow_test.py

# Module-specific testing
python scripts/testing/run_module1_tests.py
```

### 🛑 Clean Shutdown
```bash
# Stop all services cleanly
./scripts/stop_all_services.sh

# Or force kill if needed
pkill -f "uvicorn"
pkill -f "celery"
pkill -f "streamlit"
```

## Port Configuration

### Service Ports
- **FastAPI Backend**: 8000 (standardized in v4.7.0)
- **Streamlit Frontend**: 8005
- **PostgreSQL**: 5432
- **Redis**: 6379
- **Qdrant**: 6333
- **Ollama**: 11434

### Process Management
- PID files stored in project root: `.fastapi.pid`, `.celery.pid`, `.streamlit.pid`
- Use `ps aux | grep -E "(uvicorn|celery|streamlit)"` to check running processes

## Troubleshooting

### Common Issues

#### Service Conflicts
```bash
# Check for existing processes
ps aux | grep -E "(uvicorn|celery|streamlit)"

# Clean restart
./scripts/stop_all_services.sh
./scripts/start_all_services_local.sh
```

#### Database Schema Issues
```bash
# Fix missing columns (most common issue)
python scripts/database/fix_missing_columns.py

# Check database connection
python -c "from app.shared.database import get_db; next(get_db())"
```

#### Import Errors
```bash
# Verify Python environment
source venv/bin/activate
pip install -r requirements.txt

# Check imports
python -c "from app.main import app; print('Backend imports OK')"
```

### Log Locations
- **FastAPI**: `logs/fastapi.log`
- **Celery**: `logs/celery.log`
- **Streamlit**: `logs/streamlit.log`
- **Ollama**: `logs/ollama.log`

## Version History

### v4.8.0 (Current)
- ✅ Frontend deprecation fixes (37 `use_container_width` replacements)
- ✅ Real document OCR validation (88-92% accuracy)
- ✅ Comprehensive script documentation

### v4.7.0
- ✅ Port 8000 standardization
- ✅ Complete API workflow validation
- ✅ Enhanced service management scripts

### v4.6.0
- ✅ Database schema completion
- ✅ Production-ready deployment scripts
- ✅ Comprehensive testing framework

---

**Developed by**: [Muaaz Bin Saeed](https://github.com/Muaazbinsaeed/)
**Repository**: [AI Social Support App](https://github.com/Muaazbinsaeed/ai-social-support-app)