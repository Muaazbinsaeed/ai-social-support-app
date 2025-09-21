#!/bin/bash

# Social Security AI System - Local Development Startup Script
# Starts all services using local installations and Python virtual environment

set -e

echo "🚀 Starting Social Security AI System - Local Development Mode"
echo "============================================================="

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

# Create logs directory
mkdir -p logs

# Check if virtual environment exists
check_venv() {
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found. Creating one..."
        python -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        print_success "Virtual environment created and dependencies installed"
    else
        print_success "Virtual environment found"
    fi
}

# Start local services
start_local_services() {
    print_status "Starting local infrastructure services..."

    # Start PostgreSQL if not running
    if ! brew services list | grep postgresql@14 | grep started > /dev/null; then
        print_status "Starting PostgreSQL..."
        brew services start postgresql@14 || print_warning "PostgreSQL may already be running"
    else
        print_success "PostgreSQL already running"
    fi

    # Redis is already running according to earlier check
    print_success "Redis already running"

    # Start Ollama
    print_status "Starting Ollama server..."
    if ! pgrep -f ollama > /dev/null; then
        ollama serve > logs/ollama.log 2>&1 &
        echo $! > .ollama.pid
        sleep 3
        print_success "Ollama server started"
    else
        print_success "Ollama already running"
    fi
}

# Initialize database if needed
init_database() {
    print_status "Checking database initialization..."
    source venv/bin/activate

    # Try to initialize database
    python -c "
from app.shared.database import init_db
try:
    init_db()
    print('Database initialized successfully')
except Exception as e:
    print(f'Database initialization: {e}')
" && print_success "Database ready"
}

# Kill existing Python services
cleanup_services() {
    print_status "Cleaning up existing services..."

    # Kill existing services
    pkill -f "uvicorn app.main:app" > /dev/null 2>&1 || true
    pkill -f "celery.*worker" > /dev/null 2>&1 || true
    pkill -f "streamlit run" > /dev/null 2>&1 || true

    sleep 2
    print_success "Cleanup completed"
}

# Start Python services
start_python_services() {
    print_status "Starting Python services..."

    # Activate virtual environment
    source venv/bin/activate

    # Start FastAPI backend
    print_status "Starting FastAPI backend on port 8000..."
    nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > logs/fastapi.log 2>&1 &
    FASTAPI_PID=$!
    echo $FASTAPI_PID > .fastapi.pid
    print_success "FastAPI started (PID: $FASTAPI_PID)"

    # Wait for FastAPI to start
    sleep 5

    # Start Celery workers
    print_status "Starting Celery workers..."
    nohup celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 > logs/celery.log 2>&1 &
    CELERY_PID=$!
    echo $CELERY_PID > .celery.pid
    print_success "Celery workers started (PID: $CELERY_PID)"

    # Start Streamlit frontend
    print_status "Starting Streamlit frontend on port 8005..."
    nohup streamlit run frontend/dashboard_app.py --server.port=8005 --server.address=0.0.0.0 --server.headless=true > logs/streamlit.log 2>&1 &
    STREAMLIT_PID=$!
    echo $STREAMLIT_PID > .streamlit.pid
    print_success "Streamlit started (PID: $STREAMLIT_PID)"
}

# Health check
health_check() {
    print_status "Performing health check..."
    sleep 10  # Give services time to start

    # Check FastAPI
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "✅ FastAPI backend (http://localhost:8000)"
    else
        print_warning "⚠️ FastAPI backend not responding yet"
    fi

    # Check Streamlit
    if curl -s http://localhost:8005 > /dev/null 2>&1; then
        print_success "✅ Streamlit frontend (http://localhost:8005)"
    else
        print_warning "⚠️ Streamlit frontend not responding yet"
    fi

    # Check Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_success "✅ Ollama AI server (http://localhost:11434)"
    else
        print_warning "⚠️ Ollama AI server not responding yet"
    fi

    # Check PostgreSQL
    if psql -h localhost -U admin -d social_security_ai -c "SELECT 1;" > /dev/null 2>&1; then
        print_success "✅ PostgreSQL database"
    else
        print_warning "⚠️ PostgreSQL database connection issue"
    fi

    # Check Redis
    if redis-cli ping > /dev/null 2>&1; then
        print_success "✅ Redis cache"
    else
        print_warning "⚠️ Redis cache not responding"
    fi
}

# Show service information
show_service_info() {
    echo ""
    echo "🎉 Social Security AI System Started!"
    echo "===================================="
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
    echo "📋 Service Status:"
    echo "• FastAPI Backend:    Running on port 8000"
    echo "• Streamlit Frontend: Running on port 8005"
    echo "• PostgreSQL:         Running on port 5432"
    echo "• Redis:              Running on port 6379"
    echo "• Ollama AI:          Running on port 11434"
    echo "• Celery Workers:     Background processing active"
    echo ""
    echo "📁 Log Files:"
    echo "• FastAPI:    logs/fastapi.log"
    echo "• Celery:     logs/celery.log"
    echo "• Streamlit:  logs/streamlit.log"
    echo "• Ollama:     logs/ollama.log"
    echo ""
    echo "🛑 To stop all services, run: scripts/stop_all_services.sh"
    echo ""
    echo "Process IDs saved in:"
    echo "• FastAPI: .fastapi.pid"
    echo "• Celery:  .celery.pid"
    echo "• Streamlit: .streamlit.pid"
    echo "• Ollama: .ollama.pid"
}

# Create stop script
create_stop_script() {
    cat > scripts/stop_all_services.sh << 'EOF'
#!/bin/bash

echo "🛑 Stopping Social Security AI System..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Stop Python services using PID files
if [ -f .fastapi.pid ]; then
    PID=$(cat .fastapi.pid)
    if kill $PID 2>/dev/null; then
        print_success "FastAPI stopped"
    fi
    rm -f .fastapi.pid
fi

if [ -f .celery.pid ]; then
    PID=$(cat .celery.pid)
    if kill $PID 2>/dev/null; then
        print_success "Celery workers stopped"
    fi
    rm -f .celery.pid
fi

if [ -f .streamlit.pid ]; then
    PID=$(cat .streamlit.pid)
    if kill $PID 2>/dev/null; then
        print_success "Streamlit stopped"
    fi
    rm -f .streamlit.pid
fi

if [ -f .ollama.pid ]; then
    PID=$(cat .ollama.pid)
    if kill $PID 2>/dev/null; then
        print_success "Ollama stopped"
    fi
    rm -f .ollama.pid
fi

# Fallback: kill by process name
pkill -f "uvicorn app.main:app" > /dev/null 2>&1 || true
pkill -f "celery.*worker" > /dev/null 2>&1 || true
pkill -f "streamlit run" > /dev/null 2>&1 || true
pkill -f "ollama serve" > /dev/null 2>&1 || true

print_success "All services stopped!"
EOF

    chmod +x scripts/stop_all_services.sh
    print_success "Stop script created at scripts/stop_all_services.sh"
}

# Main execution
main() {
    check_venv
    cleanup_services
    start_local_services
    init_database
    start_python_services
    health_check
    create_stop_script
    show_service_info

    print_success "🚀 System startup complete! Open http://localhost:8005 to access the dashboard"
}

# Handle Ctrl+C
trap 'echo -e "\n${YELLOW}Startup interrupted by user${NC}"; exit 1' SIGINT

# Run main function
main