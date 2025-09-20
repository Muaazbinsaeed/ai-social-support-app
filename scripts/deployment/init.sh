#!/bin/bash

# Social Security AI System - Complete Initialization Script
# This script performs first-time setup of the entire system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

# System requirements
MIN_DOCKER_VERSION="20.10.0"
MIN_DOCKER_COMPOSE_VERSION="1.29.0"
MIN_PYTHON_VERSION="3.9"
REQUIRED_MEMORY_GB=8
REQUIRED_DISK_GB=20

echo -e "${PURPLE}🚀 Social Security AI System - Complete Initialization${NC}"
echo "============================================================="

# Function to print colored messages
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${PURPLE}=== $1 ===${NC}"
}

# Function to check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare versions
version_gte() {
    [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

# Function to get system info
get_system_info() {
    print_header "System Information"

    echo "Operating System: $(uname -s) $(uname -r)"
    echo "Architecture: $(uname -m)"
    echo "Current User: $(whoami)"
    echo "Working Directory: $(pwd)"

    # Memory check
    if command_exists free; then
        local memory_gb=$(free -g | awk '/^Mem:/{print $2}')
        echo "Available Memory: ${memory_gb}GB"
        if [ "$memory_gb" -lt "$REQUIRED_MEMORY_GB" ]; then
            print_warning "System has less than ${REQUIRED_MEMORY_GB}GB RAM. Performance may be affected."
        fi
    elif command_exists sysctl; then
        # macOS
        local memory_bytes=$(sysctl -n hw.memsize)
        local memory_gb=$((memory_bytes / 1024 / 1024 / 1024))
        echo "Available Memory: ${memory_gb}GB"
        if [ "$memory_gb" -lt "$REQUIRED_MEMORY_GB" ]; then
            print_warning "System has less than ${REQUIRED_MEMORY_GB}GB RAM. Performance may be affected."
        fi
    fi

    # Disk space check (macOS compatible)
    if command -v df > /dev/null; then
        local disk_space_kb=$(df . | awk 'NR==2 {print $4}')
        local disk_space=$((disk_space_kb / 1024 / 1024))
        echo "Available Disk Space: ${disk_space}GB"
        if [ "$disk_space" -lt "$REQUIRED_DISK_GB" ]; then
            print_warning "Less than ${REQUIRED_DISK_GB}GB disk space available. Consider freeing up space."
        fi
    else
        echo "Available Disk Space: Unable to determine"
    fi
}

# Function to check system requirements
check_requirements() {
    print_header "Checking System Requirements"

    local all_requirements_met=true

    # Check Python
    if command_exists python3; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        echo "Python: $python_version"
        if ! version_gte "$python_version" "$MIN_PYTHON_VERSION"; then
            print_error "Python $MIN_PYTHON_VERSION or higher is required"
            all_requirements_met=false
        else
            print_success "Python version OK"
        fi
    else
        print_error "Python 3 is not installed"
        all_requirements_met=false
    fi

    # Check pip
    if command_exists pip3; then
        print_success "pip3 is available"
    else
        print_error "pip3 is not installed"
        all_requirements_met=false
    fi

    # Check Docker
    if command_exists docker; then
        local docker_version=$(docker --version | cut -d' ' -f3 | sed 's/,//')
        echo "Docker: $docker_version"
        if ! version_gte "$docker_version" "$MIN_DOCKER_VERSION"; then
            print_warning "Docker $MIN_DOCKER_VERSION or higher is recommended"
        else
            print_success "Docker version OK"
        fi

        # Check if Docker daemon is running
        if docker info >/dev/null 2>&1; then
            print_success "Docker daemon is running"
        else
            print_error "Docker daemon is not running. Please start Docker."
            all_requirements_met=false
        fi
    else
        print_error "Docker is not installed"
        echo "Please install Docker from: https://docs.docker.com/get-docker/"
        all_requirements_met=false
    fi

    # Check Docker Compose (including plugin)
    if command_exists docker-compose; then
        local compose_version=$(docker-compose --version | cut -d' ' -f3 | sed 's/,//')
        echo "Docker Compose: $compose_version"
        if ! version_gte "$compose_version" "$MIN_DOCKER_COMPOSE_VERSION"; then
            print_warning "Docker Compose $MIN_DOCKER_COMPOSE_VERSION or higher is recommended"
        else
            print_success "Docker Compose version OK"
        fi
    elif docker compose version > /dev/null 2>&1; then
        local compose_version=$(docker compose version | grep -o 'v[0-9]*\.[0-9]*\.[0-9]*' | head -1 | sed 's/v//')
        echo "Docker Compose (plugin): $compose_version"
        print_success "Docker Compose plugin available"
    else
        print_error "Docker Compose is not installed"
        all_requirements_met=false
    fi

    # Check curl
    if command_exists curl; then
        print_success "curl is available"
    else
        print_error "curl is required but not installed"
        all_requirements_met=false
    fi

    if [ "$all_requirements_met" = false ]; then
        print_error "Some requirements are not met. Please install missing components."
        exit 1
    fi

    print_success "All system requirements met!"
}

# Function to create project structure
create_project_structure() {
    print_header "Creating Project Structure"

    cd "$PROJECT_ROOT"

    # Create required directories
    local directories=(
        "uploads"
        "logs"
        "backups"
        "tests/integration"
        "tests/e2e"
        "tests/load"
        "scripts"
    )

    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_status "Created directory: $dir"
        else
            print_status "Directory exists: $dir"
        fi
    done

    # Set proper permissions
    chmod -R 755 deploy/
    chmod -R 755 scripts/

    print_success "Project structure created!"
}

# Function to validate environment file
validate_environment_file() {
    print_header "Validating Environment Configuration"

    if [ ! -f "$ENV_FILE" ]; then
        print_error ".env file not found!"
        print_status "Creating default .env file..."

        # Create a default .env file
        cat > "$ENV_FILE" << 'EOF'
# Social Security AI System - Environment Configuration
# Development Environment Settings

# Environment
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# Security Configuration
JWT_SECRET_KEY=development-jwt-secret-key-32-chars-minimum-length
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Configuration
POSTGRES_PASSWORD=postgres123
DATABASE_URL=postgresql://admin:postgres123@postgres:5432/social_security_ai
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# AI Configuration
OLLAMA_URL=http://ollama:11434
OLLAMA_REQUEST_TIMEOUT=300
OLLAMA_MAX_RETRIES=3

# Qdrant Vector Database
QDRANT_URL=http://qdrant:6333

# File Upload Configuration
MAX_FILE_SIZE=52428800
ALLOWED_EXTENSIONS=pdf,jpg,jpeg,png
UPLOAD_DIR=./uploads

# Processing Configuration
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
CELERY_WORKER_CONCURRENCY=2
CELERY_TASK_TIME_LIMIT=600
CELERY_TASK_SOFT_TIME_LIMIT=300

# Monitoring Configuration
ENABLE_METRICS=true
HEALTH_CHECK_INTERVAL=30

# Business Rules Configuration
INCOME_THRESHOLD_AED=4000
BALANCE_THRESHOLD_AED=1500
CONFIDENCE_THRESHOLD=0.7
AUTO_APPROVAL_THRESHOLD=0.8

# Test User Credentials
TEST_USER1_USERNAME=user1
TEST_USER1_PASSWORD=password123
TEST_USER2_USERNAME=user2
TEST_USER2_PASSWORD=password123
EOF

        print_success "Default .env file created!"
        print_warning "Please review and update .env file with your specific configuration"
    else
        print_success ".env file exists"

        # Check for required variables
        local required_vars=(
            "DATABASE_URL"
            "REDIS_URL"
            "JWT_SECRET_KEY"
            "OLLAMA_URL"
        )

        for var in "${required_vars[@]}"; do
            if grep -q "^$var=" "$ENV_FILE"; then
                print_success "Required variable $var is set"
            else
                print_error "Required variable $var is missing from .env file"
            fi
        done
    fi
}

# Function to install Python dependencies
install_python_dependencies() {
    print_header "Installing Python Dependencies"

    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        print_error "requirements.txt not found!"
        exit 1
    fi

    print_status "Checking Python dependencies..."

    # Skip installation if Docker is available (dependencies will be in containers)
    if docker info > /dev/null 2>&1; then
        print_success "Using Docker containers for Python dependencies - skipping host installation"
    else
        print_status "Installing Python packages..."
        pip3 install -r "$REQUIREMENTS_FILE" --break-system-packages --user
        print_success "Python dependencies installed!"
    fi
}

# Function to pull Docker images
pull_docker_images() {
    print_header "Pulling Docker Images"

    print_status "Pulling base images..."
    docker pull postgres:15
    docker pull redis:7-alpine
    docker pull qdrant/qdrant:latest
    docker pull ollama/ollama:latest

    print_success "Docker images pulled!"
}

# Function to build custom images
build_custom_images() {
    print_header "Building Custom Docker Images"

    cd "$PROJECT_ROOT"

    print_status "Building application image..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache

    print_success "Custom images built!"
}

# Function to initialize database
initialize_database() {
    print_header "Initializing Database"

    # Start only database service
    print_status "Starting PostgreSQL service..."
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d postgres

    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres pg_isready -U admin >/dev/null 2>&1; then
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "Database failed to start"
            exit 1
        fi

        echo -n "."
        sleep 2
        ((attempt++))
    done

    print_success "Database is ready!"

    # Stop database for now
    docker compose -f "$DOCKER_COMPOSE_FILE" stop postgres
}

# Function to create initialization SQL
create_init_sql() {
    print_header "Creating Database Initialization Script"

    cat > "$PROJECT_ROOT/scripts/init.sql" << 'EOF'
-- Social Security AI Database Initialization
-- This script is run automatically by PostgreSQL on first startup

-- Ensure the database exists
SELECT 'CREATE DATABASE social_security_ai'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'social_security_ai');

-- Connect to the database
\c social_security_ai;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set default permissions
GRANT ALL PRIVILEGES ON DATABASE social_security_ai TO admin;
EOF

    print_success "Database initialization script created!"
}

# Function to set up monitoring
setup_monitoring() {
    print_header "Setting Up Monitoring"

    # Create health check script
    cat > "$PROJECT_ROOT/scripts/health_monitor.sh" << 'EOF'
#!/bin/bash

# Simple health monitoring script
echo "=== Health Check $(date) ==="

# Check API
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo "✅ API: Healthy"
else
    echo "❌ API: Unhealthy"
fi

# Check Frontend
if curl -f -s http://localhost:8005 > /dev/null; then
    echo "✅ Frontend: Healthy"
else
    echo "❌ Frontend: Unhealthy"
fi

# Check Docker containers
echo "📊 Container Status:"
docker-compose ps --format "table {{.Name}}\t{{.Status}}"

echo "==========================================\n"
EOF

    chmod +x "$PROJECT_ROOT/scripts/health_monitor.sh"
    print_success "Monitoring setup completed!"
}

# Function to create useful aliases
create_aliases() {
    print_header "Creating Useful Aliases"

    cat > "$PROJECT_ROOT/aliases.sh" << 'EOF'
#!/bin/bash

# Useful aliases for Social Security AI System
# Source this file to add aliases to your shell

alias ss-up='make up'
alias ss-down='make down'
alias ss-logs='make logs'
alias ss-test='make test'
alias ss-status='make status'
alias ss-health='make health'
alias ss-verify='make verify'
alias ss-shell-api='make shell-api'
alias ss-shell-db='make shell-db'
alias ss-backup='make backup'

echo "Social Security AI aliases loaded!"
echo "Available commands: ss-up, ss-down, ss-logs, ss-test, ss-status, ss-health, ss-verify"
EOF

    chmod +x "$PROJECT_ROOT/aliases.sh"
    print_success "Aliases created! Source aliases.sh to use them."
}

# Function to create quick start guide
create_quick_start_guide() {
    print_header "Creating Quick Start Guide"

    cat > "$PROJECT_ROOT/QUICK_START.md" << 'EOF'
# Social Security AI - Quick Start Guide

## System Overview
This is a complete AI-powered social security application processing system that automates document verification and eligibility decisions.

## Quick Commands

### Start the System
```bash
make up              # Start all services
make status          # Check service status
make verify          # Verify system functionality
```

### Development
```bash
make test            # Run all tests
make logs            # View system logs
make shell-api       # Access API container
make shell-db        # Access database
```

### Maintenance
```bash
make backup          # Create system backup
make clean           # Clean up containers
make reset           # Reset entire system (destroys data)
```

## Access Points

- **Dashboard**: http://localhost:8005
- **API Documentation**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health

## Default Test Users

- **Username**: user1, **Password**: password123
- **Username**: user2, **Password**: password123

## Troubleshooting

1. **Services won't start**: Check Docker is running and ports are available
2. **AI not working**: Ollama models may still be downloading
3. **Database errors**: Run `make reset` to reinitialize
4. **Performance issues**: Ensure at least 8GB RAM available

## Support

- Check logs: `make logs`
- Run health check: `make health`
- Verify system: `make verify`
- Reset if needed: `make reset`

## File Structure

```
├── app/                 # Main application code
├── frontend/            # Streamlit dashboard
├── deploy/              # Deployment scripts
├── scripts/             # Utility scripts
├── tests/               # Test suites
├── uploads/             # File uploads
├── logs/                # Application logs
└── backups/             # System backups
```
EOF

    print_success "Quick start guide created!"
}

# Function to run final verification
run_final_verification() {
    print_header "Running Final Verification"

    # Check all files exist
    local critical_files=(
        "$DOCKER_COMPOSE_FILE"
        "$ENV_FILE"
        "$REQUIREMENTS_FILE"
        "$PROJECT_ROOT/deploy/up.sh"
        "$PROJECT_ROOT/deploy/down.sh"
        "$PROJECT_ROOT/Makefile"
    )

    for file in "${critical_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "✅ $(basename "$file")"
        else
            print_error "❌ $(basename "$file") missing"
        fi
    done

    # Check directories
    local critical_dirs=(
        "$PROJECT_ROOT/uploads"
        "$PROJECT_ROOT/logs"
        "$PROJECT_ROOT/backups"
        "$PROJECT_ROOT/app"
        "$PROJECT_ROOT/frontend"
        "$PROJECT_ROOT/tests"
    )

    for dir in "${critical_dirs[@]}"; do
        if [ -d "$dir" ]; then
            print_success "✅ $(basename "$dir")/"
        else
            print_error "❌ $(basename "$dir")/ missing"
        fi
    done
}

# Function to show completion message
show_completion_message() {
    echo ""
    echo -e "${GREEN}🎉 Social Security AI System Initialization Complete!${NC}"
    echo "============================================================="
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Review and update .env file if needed"
    echo "2. Start the system: ${GREEN}make up${NC}"
    echo "3. Load test data: ${GREEN}make seed-data${NC}"
    echo "4. Access dashboard: ${GREEN}http://localhost:8005${NC}"
    echo "5. Run tests: ${GREEN}make test${NC}"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "• make help          - Show all available commands"
    echo "• make status        - Check system status"
    echo "• make logs          - View system logs"
    echo "• make verify        - Verify system functionality"
    echo "• make health        - Run health checks"
    echo ""
    echo -e "${PURPLE}Documentation:${NC}"
    echo "• Quick Start: QUICK_START.md"
    echo "• API Docs: http://localhost:8000/docs (when running)"
    echo "• Health Check: http://localhost:8000/health (when running)"
    echo ""
    echo -e "${GREEN}System is ready for deployment!${NC}"
}

# Main initialization sequence
main() {
    cd "$PROJECT_ROOT"

    # System information
    get_system_info

    # Check requirements
    check_requirements

    # Create project structure
    create_project_structure

    # Validate environment
    validate_environment_file

    # Install dependencies
    install_python_dependencies

    # Docker setup
    pull_docker_images
    build_custom_images

    # Database setup
    create_init_sql
    initialize_database

    # Additional setup
    setup_monitoring
    create_aliases
    create_quick_start_guide

    # Final verification
    run_final_verification

    # Show completion message
    show_completion_message
}

# Run the main function
main "$@"