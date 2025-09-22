#!/bin/bash

# AI Social Support App - Complete Setup Script
# Developed by: Muaaz Bin Saeed
# Repository: https://github.com/Muaazbinsaeed/ai-social-support-app

set -e  # Exit on any error

echo "🚀 AI Social Support App - Complete Setup"
echo "========================================"
echo "👨‍💻 Developed by: Muaaz Bin Saeed"
echo "🔗 Repository: https://github.com/Muaazbinsaeed/ai-social-support-app"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Python 3.9+ is installed
check_python() {
    print_info "Checking Python installation..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d " " -f 2)
        print_status "Python $PYTHON_VERSION found"
    else
        print_error "Python 3.9+ is required but not found!"
        exit 1
    fi
}

# Create virtual environment
setup_venv() {
    print_info "Setting up virtual environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi

    # Activate virtual environment
    source venv/bin/activate
    print_status "Virtual environment activated"
}

# Install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_status "Python dependencies installed"
}

# Setup environment file
setup_environment() {
    print_info "Setting up environment configuration..."
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_status "Environment file created from template"
            print_warning "Please update .env file with your configurations"
        else
            print_error ".env.example file not found"
            exit 1
        fi
    else
        print_warning ".env file already exists"
    fi
}

# Initialize database
init_database() {
    print_info "Initializing database..."
    python -c "from app.shared.database import init_db; init_db()" 2>/dev/null || {
        print_warning "Database initialization failed (may need Docker services)"
    }
}

# Setup directories
setup_directories() {
    print_info "Creating required directories..."
    mkdir -p uploads logs
    touch logs/.gitkeep uploads/.gitkeep
    print_status "Directories created"
}

# Check Docker (optional)
check_docker() {
    print_info "Checking Docker installation (optional)..."
    if command -v docker &> /dev/null; then
        print_status "Docker found - you can use docker-compose for infrastructure"
        if command -v docker-compose &> /dev/null; then
            print_status "Docker Compose found"
        else
            print_warning "Docker Compose not found - install for easy infrastructure setup"
        fi
    else
        print_warning "Docker not found - you'll need to install PostgreSQL and Redis manually"
    fi
}

# Display next steps
show_next_steps() {
    echo ""
    echo "🎉 Setup Complete!"
    echo "================="
    echo ""
    echo "📋 Next Steps:"
    echo "1. Update .env file with your database and service configurations"
    echo "2. Start infrastructure services:"
    echo "   - Option A (Docker): docker-compose up -d postgres redis qdrant ollama"
    echo "   - Option B (Manual): Install PostgreSQL, Redis, and Ollama locally"
    echo ""
    echo "3. Download AI models:"
    echo "   docker exec \$(docker-compose ps -q ollama) ollama pull moondream:1.8b"
    echo "   docker exec \$(docker-compose ps -q ollama) ollama pull qwen2:1.5b"
    echo "   docker exec \$(docker-compose ps -q ollama) ollama pull nomic-embed-text"
    echo ""
    echo "4. Start the application:"
    echo "   # Terminal 1 - Backend"
    echo "   source venv/bin/activate"
    echo "   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    echo ""
    echo "   # Terminal 2 - Workers"
    echo "   source venv/bin/activate"
    echo "   celery -A app.workers.celery_app worker --loglevel=info"
    echo ""
    echo "   # Terminal 3 - Frontend"
    echo "   source venv/bin/activate"
    echo "   streamlit run frontend/dashboard_app.py --server.port=8005"
    echo ""
    echo "🔗 Access Points:"
    echo "   📊 Dashboard: http://localhost:8005"
    echo "   🔧 API Docs: http://localhost:8000/docs"
    echo "   💚 Health: http://localhost:8000/health"
    echo ""
    echo "🧪 Test the system:"
    echo "   python tests/demo_workflow_test.py"
    echo ""
    echo "For detailed documentation, see README.md"
}

# Main setup flow
main() {
    check_python
    setup_venv
    install_dependencies
    setup_environment
    setup_directories
    init_database
    check_docker
    show_next_steps
}

# Run setup
main