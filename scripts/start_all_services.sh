#!/bin/bash

# Social Security AI System - Complete Service Startup Script
# This script starts all required services for the complete system

set -e

echo "🚀 Starting Social Security AI System - All Services"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if Docker is running
check_docker() {
    print_status "Checking Docker status..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop first."
        exit 1
    fi
    print_success "Docker is running"
}

# Start infrastructure services with Docker
start_infrastructure() {
    print_status "Starting infrastructure services (PostgreSQL, Redis, Qdrant, Ollama)..."

    # Stop any existing containers
    docker compose down > /dev/null 2>&1 || true

    # Start only infrastructure services
    docker compose up -d postgres redis qdrant ollama

    print_status "Waiting for services to be ready..."
    sleep 10

    # Check service health
    print_status "Checking PostgreSQL..."
    docker compose exec -T postgres pg_isready -U admin > /dev/null 2>&1 && print_success "PostgreSQL is ready" || print_warning "PostgreSQL not ready yet"

    print_status "Checking Redis..."
    docker compose exec -T redis redis-cli ping > /dev/null 2>&1 && print_success "Redis is ready" || print_warning "Redis not ready yet"

    print_success "Infrastructure services started"
}

# Download required AI models
setup_ai_models() {
    print_status "Setting up AI models..."

    # Wait for Ollama to be ready
    sleep 5

    print_status "Downloading moondream:1.8b model..."
    docker compose exec -T ollama ollama pull moondream:1.8b &

    print_status "Downloading nomic-embed-text model..."
    docker compose exec -T ollama ollama pull nomic-embed-text &

    # qwen2:1.5b should already be available based on the list we saw
    print_status "Checking qwen2:1.5b model..."
    docker compose exec -T ollama ollama list | grep qwen2:1.5b && print_success "qwen2:1.5b already available"

    wait # Wait for background downloads to complete
    print_success "AI models setup complete"
}

# Initialize database
init_database() {
    print_status "Initializing database..."

    # Activate virtual environment and run database initialization
    source venv/bin/activate
    python -c "from app.shared.database import init_db; init_db()" && print_success "Database initialized"
}

# Start Python services in virtual environment
start_python_services() {
    print_status "Starting Python services in virtual environment..."

    # Activate virtual environment
    source venv/bin/activate

    # Kill any existing Python services on the required ports
    print_status "Cleaning up existing services..."
    pkill -f "uvicorn app.main:app" > /dev/null 2>&1 || true
    pkill -f "celery.*worker" > /dev/null 2>&1 || true
    pkill -f "streamlit run" > /dev/null 2>&1 || true

    sleep 2

    # Start FastAPI backend
    print_status "Starting FastAPI backend on port 8000..."
    nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > logs/fastapi.log 2>&1 &
    FASTAPI_PID=$!
    echo $FASTAPI_PID > .fastapi.pid

    # Wait for FastAPI to start
    sleep 5

    # Start Celery workers
    print_status "Starting Celery workers..."
    nohup celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 > logs/celery.log 2>&1 &
    CELERY_PID=$!
    echo $CELERY_PID > .celery.pid

    # Start Streamlit frontend
    print_status "Starting Streamlit frontend on port 8005..."
    nohup streamlit run frontend/dashboard_app.py --server.port=8005 --server.address=0.0.0.0 --server.headless=true > logs/streamlit.log 2>&1 &
    STREAMLIT_PID=$!
    echo $STREAMLIT_PID > .streamlit.pid

    print_success "Python services started"
}

# Health check all services
health_check() {
    print_status "Performing comprehensive health check..."

    sleep 10  # Give services time to fully start

    # Check FastAPI
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "✅ FastAPI backend (http://localhost:8000)"
    else
        print_error "❌ FastAPI backend not responding"
    fi

    # Check Streamlit
    if curl -s http://localhost:8005 > /dev/null 2>&1; then
        print_success "✅ Streamlit frontend (http://localhost:8005)"
    else
        print_error "❌ Streamlit frontend not responding"
    fi

    # Check PostgreSQL
    if docker compose exec -T postgres pg_isready -U admin > /dev/null 2>&1; then
        print_success "✅ PostgreSQL database"
    else
        print_error "❌ PostgreSQL database not ready"
    fi

    # Check Redis
    if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_success "✅ Redis cache"
    else
        print_error "❌ Redis cache not ready"
    fi

    # Check Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_success "✅ Ollama AI server"
    else
        print_error "❌ Ollama AI server not ready"
    fi
}

# Display service information
show_service_info() {
    echo ""
    echo "🎉 All services are starting up!"
    echo "================================="
    echo ""
    echo "📊 Access Points:"
    echo "• Frontend Dashboard: http://localhost:8005"
    echo "• API Documentation: http://localhost:8000/docs"
    echo "• API Health Check:  http://localhost:8000/health"
    echo ""
    echo "🔐 Test Credentials:"
    echo "• Username: user1  Password: password123"
    echo "• Username: user2  Password: password123"
    echo ""
    echo "📋 Service Ports:"
    echo "• Streamlit Frontend: 8005"
    echo "• FastAPI Backend:    8000"
    echo "• PostgreSQL:         5432"
    echo "• Redis:              6379"
    echo "• Qdrant:             6333"
    echo "• Ollama:             11434"
    echo ""
    echo "📁 Log Files:"
    echo "• FastAPI:    logs/fastapi.log"
    echo "• Celery:     logs/celery.log"
    echo "• Streamlit:  logs/streamlit.log"
    echo ""
    echo "🛑 To stop all services, run: scripts/stop_all_services.sh"
}

# Create logs directory
mkdir -p logs

# Main execution
main() {
    echo "Starting Social Security AI System..."

    check_docker
    start_infrastructure
    setup_ai_models &  # Run in background
    init_database
    start_python_services
    health_check
    show_service_info

    print_success "🚀 System startup complete! Access the dashboard at http://localhost:8005"
}

# Run main function
main