#!/bin/bash

# Social Security AI System Setup Script
# Complete automated setup for development and production

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="Social Security AI"
REQUIRED_DOCKER_VERSION="24.0"
REQUIRED_COMPOSE_VERSION="2.20"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare versions
version_compare() {
    if [[ $1 == $2 ]]; then
        echo "0"
    elif [[ $1 > $2 ]]; then
        echo "1"
    else
        echo "-1"
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command_exists docker; then
        log_error "Docker is not installed. Please install Docker first."
        log_info "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi

    DOCKER_VERSION=$(docker --version | cut -d ' ' -f3 | cut -d ',' -f1)
    log_info "Docker version: $DOCKER_VERSION"

    # Check Docker Compose
    if ! command_exists docker-compose; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        log_info "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi

    COMPOSE_VERSION=$(docker-compose --version | cut -d ' ' -f4 | cut -d ',' -f1)
    log_info "Docker Compose version: $COMPOSE_VERSION"

    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi

    log_success "Prerequisites check completed"
}

# Setup environment
setup_environment() {
    log_info "Setting up environment..."

    # Create .env file if it doesn't exist
    if [[ ! -f .env ]]; then
        if [[ -f .env.example ]]; then
            cp .env.example .env
            log_success "Created .env file from .env.example"
        else
            log_error ".env.example file not found"
            exit 1
        fi
    else
        log_info ".env file already exists"
    fi

    # Create necessary directories
    log_info "Creating directories..."
    mkdir -p uploads logs scripts/backups
    chmod 755 uploads logs

    # Create .gitkeep files
    touch uploads/.gitkeep logs/.gitkeep

    log_success "Environment setup completed"
}

# Start infrastructure services
start_infrastructure() {
    log_info "Starting infrastructure services..."

    # Start core services first
    log_info "Starting PostgreSQL, Redis, and Qdrant..."
    docker-compose up -d postgres redis qdrant

    # Wait for databases to be ready
    log_info "Waiting for databases to initialize..."
    sleep 30

    # Check database connectivity
    log_info "Checking database connectivity..."
    max_attempts=30
    attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        if docker-compose exec -T postgres pg_isready -U admin >/dev/null 2>&1; then
            log_success "PostgreSQL is ready"
            break
        fi

        attempt=$((attempt + 1))
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "PostgreSQL failed to start within timeout"
            exit 1
        fi

        log_info "Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
        sleep 5
    done

    # Check Redis connectivity
    if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        log_success "Redis is ready"
    else
        log_warning "Redis may not be ready, but continuing..."
    fi

    log_success "Infrastructure services started"
}

# Initialize database
initialize_database() {
    log_info "Initializing database..."

    # Wait a bit more for database to be fully ready
    sleep 10

    # Run database initialization
    if docker-compose exec -T fastapi-app python scripts/init_db.py 2>/dev/null; then
        log_success "Database initialized successfully"
    else
        log_warning "Database initialization may have failed, will retry after app starts"
    fi
}

# Start AI services
start_ai_services() {
    log_info "Starting AI model server..."

    # Start Ollama
    docker-compose up -d ollama

    log_info "Waiting for Ollama to start..."
    sleep 60

    # Check if Ollama is ready
    max_attempts=20
    attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            log_success "Ollama is ready"
            break
        fi

        attempt=$((attempt + 1))
        if [[ $attempt -eq $max_attempts ]]; then
            log_warning "Ollama may not be ready, but continuing..."
            break
        fi

        log_info "Waiting for Ollama... (attempt $attempt/$max_attempts)"
        sleep 10
    done

    # Download AI models
    log_info "Downloading AI models (this may take several minutes)..."

    log_info "Downloading moondream:1.8b..."
    if ! docker exec $(docker-compose ps -q ollama) ollama pull moondream:1.8b; then
        log_warning "Failed to download moondream:1.8b"
    fi

    log_info "Downloading qwen2:1.5b..."
    if ! docker exec $(docker-compose ps -q ollama) ollama pull qwen2:1.5b; then
        log_warning "Failed to download qwen2:1.5b"
    fi

    log_info "Downloading nomic-embed-text..."
    if ! docker exec $(docker-compose ps -q ollama) ollama pull nomic-embed-text; then
        log_warning "Failed to download nomic-embed-text"
    fi

    log_success "AI services setup completed"
}

# Start application services
start_applications() {
    log_info "Starting application services..."

    # Build and start all services
    docker-compose up --build -d

    log_info "Waiting for applications to start..."
    sleep 45

    log_success "Application services started"
}

# Initialize application data
initialize_application_data() {
    log_info "Initializing application data..."

    # Initialize database if not done earlier
    if ! docker-compose exec -T fastapi-app python scripts/init_db.py; then
        log_error "Failed to initialize database"
        exit 1
    fi

    # Create test users
    if docker-compose exec -T fastapi-app python scripts/seed_users.py; then
        log_success "Test users created"
    else
        log_warning "Failed to create test users"
    fi

    # Generate test data
    if docker-compose exec -T fastapi-app python scripts/generate_test_data.py; then
        log_success "Test data generated"
    else
        log_warning "Failed to generate test data"
    fi

    log_success "Application data initialization completed"
}

# Health check
perform_health_check() {
    log_info "Performing health check..."
    sleep 30

    # Check API health
    max_attempts=10
    attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            log_success "FastAPI application is healthy"
            break
        fi

        attempt=$((attempt + 1))
        if [[ $attempt -eq $max_attempts ]]; then
            log_warning "FastAPI health check failed"
            break
        fi

        log_info "Waiting for FastAPI... (attempt $attempt/$max_attempts)"
        sleep 10
    done

    # Check Streamlit
    if curl -s http://localhost:8005 >/dev/null 2>&1; then
        log_success "Streamlit dashboard is accessible"
    else
        log_warning "Streamlit dashboard may not be ready"
    fi

    # Run comprehensive health check if possible
    if docker-compose exec -T fastapi-app python scripts/health_check.py; then
        log_success "Comprehensive health check passed"
    else
        log_warning "Some health checks failed, but system may still be functional"
    fi
}

# Show final status
show_final_status() {
    echo ""
    echo "=================================================================="
    echo -e "${GREEN}🎉 SOCIAL SECURITY AI SETUP COMPLETED! 🎉${NC}"
    echo "=================================================================="
    echo ""
    echo -e "${BLUE}📊 System Status:${NC}"
    echo "   🔗 API Server:     http://localhost:8000"
    echo "   🌐 Dashboard:      http://localhost:8005"
    echo "   📚 API Docs:       http://localhost:8000/docs"
    echo "   🔍 Health Check:   http://localhost:8000/health"
    echo ""
    echo -e "${BLUE}🔑 Test Credentials:${NC}"
    echo "   Username: user1     | Password: password123"
    echo "   Username: user2     | Password: password123"
    echo "   Username: admin     | Password: admin123"
    echo "   Username: demo      | Password: demo123"
    echo ""
    echo -e "${BLUE}🚀 Getting Started:${NC}"
    echo "   1. Open http://localhost:8005 in your browser"
    echo "   2. Login with test credentials above"
    echo "   3. Follow the 3-panel workflow to submit an application"
    echo "   4. Upload sample documents from uploads/test_documents/"
    echo "   5. Watch AI process your application in real-time!"
    echo ""
    echo -e "${BLUE}🛠️  Useful Commands:${NC}"
    echo "   • View logs:        docker-compose logs [service-name]"
    echo "   • Restart service:  docker-compose restart [service-name]"
    echo "   • Stop system:      docker-compose down"
    echo "   • Health check:     python scripts/health_check.py"
    echo "   • Reset system:     python scripts/reset_system.py"
    echo ""
    echo -e "${YELLOW}⚡ Performance Tips:${NC}"
    echo "   • First AI processing may take longer as models initialize"
    echo "   • OCR processing: ~30 seconds per document"
    echo "   • Decision making: ~10-30 seconds"
    echo "   • Total processing: typically under 2 minutes"
    echo ""
    echo "=================================================================="
    echo -e "${GREEN}Ready to transform government services with AI! 🏛️✨${NC}"
    echo "=================================================================="
}

# Handle errors
handle_error() {
    log_error "Setup failed at step: $1"
    echo ""
    echo "🔧 Troubleshooting steps:"
    echo "   1. Check Docker is running: docker info"
    echo "   2. Check available space: df -h"
    echo "   3. Check logs: docker-compose logs"
    echo "   4. Try manual setup: docker-compose up -d"
    echo "   5. Reset and retry: docker-compose down -v && ./setup_system.sh"
    exit 1
}

# Main setup function
main() {
    echo ""
    echo "=================================================================="
    echo -e "${BLUE}🏛️  SOCIAL SECURITY AI SYSTEM SETUP${NC}"
    echo "=================================================================="
    echo -e "${YELLOW}AI-powered government application processing in under 2 minutes${NC}"
    echo "=================================================================="
    echo ""

    # Run setup steps
    check_prerequisites || handle_error "Prerequisites check"
    setup_environment || handle_error "Environment setup"
    start_infrastructure || handle_error "Infrastructure startup"
    start_ai_services || handle_error "AI services startup"
    start_applications || handle_error "Application startup"
    initialize_application_data || handle_error "Data initialization"
    perform_health_check || handle_error "Health check"

    show_final_status
}

# Run main function
main "$@"