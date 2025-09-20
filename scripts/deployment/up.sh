#!/bin/bash

# Social Security AI System - Startup Script
# This script starts all services in the correct order with proper health checks

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
MAX_WAIT_TIME=300  # 5 minutes max wait time
HEALTH_CHECK_INTERVAL=10

echo -e "${GREEN}🚀 Starting Social Security AI System...${NC}"
echo "======================================================="

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

# Function to check if a service is healthy
check_service_health() {
    local service_name=$1
    local health_endpoint=$2
    local max_attempts=$((MAX_WAIT_TIME / HEALTH_CHECK_INTERVAL))
    local attempt=1

    print_status "Checking health of $service_name..."

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_endpoint" > /dev/null 2>&1; then
            print_success "$service_name is healthy!"
            return 0
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "$service_name failed to become healthy after $MAX_WAIT_TIME seconds"
            return 1
        fi

        echo -n "."
        sleep $HEALTH_CHECK_INTERVAL
        ((attempt++))
    done
}

# Function to wait for database
wait_for_database() {
    print_status "Waiting for PostgreSQL database..."
    local max_attempts=$((MAX_WAIT_TIME / HEALTH_CHECK_INTERVAL))
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres pg_isready -U admin > /dev/null 2>&1; then
            print_success "PostgreSQL is ready!"
            return 0
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "PostgreSQL failed to become ready after $MAX_WAIT_TIME seconds"
            return 1
        fi

        echo -n "."
        sleep $HEALTH_CHECK_INTERVAL
        ((attempt++))
    done
}

# Function to wait for Redis
wait_for_redis() {
    print_status "Waiting for Redis..."
    local max_attempts=$((MAX_WAIT_TIME / HEALTH_CHECK_INTERVAL))
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T redis redis-cli ping | grep -q PONG; then
            print_success "Redis is ready!"
            return 0
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "Redis failed to become ready after $MAX_WAIT_TIME seconds"
            return 1
        fi

        echo -n "."
        sleep $HEALTH_CHECK_INTERVAL
        ((attempt++))
    done
}

# Function to initialize Ollama models
initialize_ollama_models() {
    print_status "Initializing Ollama AI models..."

    # Wait for Ollama service to be available
    if ! check_service_health "Ollama" "http://localhost:11434/api/tags"; then
        print_warning "Ollama service not responding, skipping model initialization"
        return 1
    fi

    # Pull required models
    local models=("qwen2:1.5b" "moondream:1.8b" "nomic-embed-text")

    for model in "${models[@]}"; do
        print_status "Pulling model: $model"
        if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T ollama ollama pull "$model"; then
            print_success "Model $model pulled successfully"
        else
            print_warning "Failed to pull model $model, will continue with fallback"
        fi
    done

    print_success "Ollama models initialization completed!"
}

# Function to run database migrations
run_database_migrations() {
    print_status "Running database migrations..."

    if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T fastapi-app python scripts/init_db.py; then
        print_success "Database migrations completed!"
    else
        print_error "Database migrations failed!"
        return 1
    fi
}

# Function to create required directories
create_directories() {
    print_status "Creating required directories..."

    mkdir -p "$PROJECT_ROOT/uploads"
    mkdir -p "$PROJECT_ROOT/logs"

    print_success "Directories created!"
}

# Function to validate environment
validate_environment() {
    print_status "Validating environment..."

    # Check if .env file exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        print_error ".env file not found! Please create it first."
        exit 1
    fi

    # Check if docker-compose file exists
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        print_error "docker-compose.yml file not found!"
        exit 1
    fi

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running! Please start Docker first."
        exit 1
    fi

    print_success "Environment validation passed!"
}

# Main startup sequence
main() {
    cd "$PROJECT_ROOT"

    # Validate environment first
    validate_environment

    # Create required directories
    create_directories

    # Start infrastructure services first
    print_status "Starting infrastructure services (Database, Redis, Qdrant)..."
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d postgres redis qdrant

    # Wait for infrastructure services
    wait_for_database
    wait_for_redis

    # Check Qdrant
    if ! check_service_health "Qdrant" "http://localhost:6333/healthz"; then
        print_warning "Qdrant health check failed, but continuing..."
    fi

    # Start Ollama service
    print_status "Starting Ollama AI service..."
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d ollama

    # Start main application
    print_status "Starting FastAPI application..."
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d fastapi-app

    # Wait for API to be healthy
    if ! check_service_health "FastAPI" "http://localhost:8000/health"; then
        print_error "FastAPI failed to start properly!"
        exit 1
    fi

    # Run database migrations
    run_database_migrations

    # Start background workers
    print_status "Starting Celery workers..."
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d celery-worker

    # Start frontend
    print_status "Starting Streamlit frontend..."
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d streamlit-frontend

    # Initialize Ollama models (non-blocking)
    initialize_ollama_models

    # Final health check
    print_status "Running final health checks..."

    # Check all services
    services_status=""

    if check_service_health "API" "http://localhost:8000/health"; then
        services_status+="✅ API Server (http://localhost:8000)\n"
    else
        services_status+="❌ API Server (http://localhost:8000)\n"
    fi

    if curl -f -s "http://localhost:8005" > /dev/null 2>&1; then
        services_status+="✅ Dashboard (http://localhost:8005)\n"
    else
        services_status+="❌ Dashboard (http://localhost:8005)\n"
    fi

    if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres pg_isready -U admin > /dev/null 2>&1; then
        services_status+="✅ PostgreSQL Database\n"
    else
        services_status+="❌ PostgreSQL Database\n"
    fi

    if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T redis redis-cli ping | grep -q PONG; then
        services_status+="✅ Redis Cache\n"
    else
        services_status+="❌ Redis Cache\n"
    fi

    if curl -f -s "http://localhost:6333/healthz" > /dev/null 2>&1; then
        services_status+="✅ Qdrant Vector DB\n"
    else
        services_status+="⚠️ Qdrant Vector DB\n"
    fi

    if curl -f -s "http://localhost:11434/api/tags" > /dev/null 2>&1; then
        services_status+="✅ Ollama AI Service\n"
    else
        services_status+="⚠️ Ollama AI Service (will use fallback)\n"
    fi

    echo ""
    echo -e "${GREEN}🎉 Social Security AI System Started Successfully!${NC}"
    echo "======================================================="
    echo -e "Services Status:"
    echo -e "$services_status"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "• Access the dashboard at: http://localhost:8005"
    echo "• View API documentation at: http://localhost:8000/docs"
    echo "• Check logs with: make logs"
    echo "• Run tests with: make test"
    echo "• Load test data with: make seed-data"
    echo ""
    echo -e "${YELLOW}Note:${NC} If Ollama models are still downloading, some AI features"
    echo "will use fallback responses until models are ready."
}

# Run the main function
main "$@"