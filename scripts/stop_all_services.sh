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
