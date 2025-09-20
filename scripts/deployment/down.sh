#!/bin/bash

# Social Security AI System - Shutdown Script
# This script gracefully stops all services and optionally cleans up resources

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
BACKUP_DIR="$PROJECT_ROOT/backups"

# Command line options
PRESERVE_DATA=true
PRESERVE_LOGS=true
BACKUP_DATA=false
FORCE_SHUTDOWN=false

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

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -f, --force         Force shutdown without confirmations"
    echo "  -c, --clean         Remove volumes (destroys all data)"
    echo "  -b, --backup        Create backup before shutdown"
    echo "  --no-logs           Don't preserve logs"
    echo ""
    echo "Examples:"
    echo "  $0                  Normal shutdown (preserves data)"
    echo "  $0 --backup         Shutdown with data backup"
    echo "  $0 --clean          Shutdown and remove all data"
    echo "  $0 --force --clean  Force shutdown and clean everything"
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -f|--force)
                FORCE_SHUTDOWN=true
                shift
                ;;
            -c|--clean)
                PRESERVE_DATA=false
                shift
                ;;
            -b|--backup)
                BACKUP_DATA=true
                shift
                ;;
            --no-logs)
                PRESERVE_LOGS=false
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Function to create backup
create_backup() {
    if [ "$BACKUP_DATA" = true ]; then
        print_status "Creating system backup..."

        # Create backup directory
        mkdir -p "$BACKUP_DIR"

        local timestamp=$(date +%Y%m%d_%H%M%S)

        # Backup database
        print_status "Backing up database..."
        if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres pg_dump -U admin social_security_ai > "$BACKUP_DIR/db_backup_$timestamp.sql" 2>/dev/null; then
            print_success "Database backup created: $BACKUP_DIR/db_backup_$timestamp.sql"
        else
            print_warning "Failed to create database backup (database may not be running)"
        fi

        # Backup uploaded files
        if [ -d "$PROJECT_ROOT/uploads" ] && [ "$(ls -A "$PROJECT_ROOT/uploads")" ]; then
            print_status "Backing up uploaded files..."
            tar -czf "$BACKUP_DIR/uploads_backup_$timestamp.tar.gz" -C "$PROJECT_ROOT" uploads/
            print_success "Files backup created: $BACKUP_DIR/uploads_backup_$timestamp.tar.gz"
        else
            print_status "No uploaded files to backup"
        fi

        # Backup logs if they exist
        if [ "$PRESERVE_LOGS" = true ] && [ -d "$PROJECT_ROOT/logs" ] && [ "$(ls -A "$PROJECT_ROOT/logs")" ]; then
            print_status "Backing up logs..."
            tar -czf "$BACKUP_DIR/logs_backup_$timestamp.tar.gz" -C "$PROJECT_ROOT" logs/
            print_success "Logs backup created: $BACKUP_DIR/logs_backup_$timestamp.tar.gz"
        fi

        print_success "Backup completed!"
    fi
}

# Function to save container logs
save_container_logs() {
    if [ "$PRESERVE_LOGS" = true ]; then
        print_status "Saving container logs..."

        # Create logs directory
        mkdir -p "$PROJECT_ROOT/logs/shutdown_$(date +%Y%m%d_%H%M%S)"
        local log_dir="$PROJECT_ROOT/logs/shutdown_$(date +%Y%m%d_%H%M%S)"

        # Save logs from each service
        local services=("fastapi-app" "celery-worker" "streamlit-frontend" "postgres" "redis" "qdrant" "ollama")

        for service in "${services[@]}"; do
            if docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q "$service" > /dev/null 2>&1; then
                print_status "Saving logs for $service..."
                docker-compose -f "$DOCKER_COMPOSE_FILE" logs "$service" > "$log_dir/${service}.log" 2>&1 || true
            fi
        done

        print_success "Container logs saved to $log_dir"
    fi
}

# Function to stop services gracefully
stop_services() {
    print_status "Stopping services gracefully..."

    # Stop frontend first (least critical)
    print_status "Stopping frontend services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" stop streamlit-frontend || true

    # Stop workers
    print_status "Stopping background workers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" stop celery-worker || true

    # Stop main API
    print_status "Stopping FastAPI application..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" stop fastapi-app || true

    # Stop AI services
    print_status "Stopping AI services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" stop ollama || true

    # Stop databases last
    print_status "Stopping database services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" stop qdrant redis postgres || true

    print_success "All services stopped gracefully!"
}

# Function to remove containers
remove_containers() {
    print_status "Removing containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" rm -f || true
    print_success "Containers removed!"
}

# Function to clean volumes
clean_volumes() {
    if [ "$PRESERVE_DATA" = false ]; then
        if [ "$FORCE_SHUTDOWN" = false ]; then
            echo -e "${RED}WARNING: This will permanently delete all data!${NC}"
            echo "This includes:"
            echo "• Database data"
            echo "• Uploaded documents"
            echo "• AI model cache"
            echo "• Application logs"
            echo ""
            read -p "Are you sure you want to continue? (y/N): " confirm
            if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                print_status "Data preservation confirmed. Skipping volume cleanup."
                return 0
            fi
        fi

        print_warning "Removing Docker volumes (this deletes all data)..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" down -v || true

        # Also remove any orphaned volumes
        docker volume prune -f || true

        print_success "Volumes cleaned!"
    else
        print_status "Preserving data volumes..."
    fi
}

# Function to clean networks
clean_networks() {
    print_status "Cleaning up networks..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans || true
    print_success "Networks cleaned!"
}

# Function to show final status
show_final_status() {
    echo ""
    echo -e "${GREEN}🛑 Social Security AI System Shutdown Complete!${NC}"
    echo "======================================================="

    if [ "$PRESERVE_DATA" = true ]; then
        echo -e "${GREEN}✅ Data preserved${NC}"
    else
        echo -e "${RED}❌ Data deleted${NC}"
    fi

    if [ "$PRESERVE_LOGS" = true ]; then
        echo -e "${GREEN}✅ Logs preserved${NC}"
    else
        echo -e "${RED}❌ Logs not preserved${NC}"
    fi

    if [ "$BACKUP_DATA" = true ]; then
        echo -e "${GREEN}✅ Backup created${NC}"
    else
        echo -e "${YELLOW}⚠️ No backup created${NC}"
    fi

    echo ""
    echo -e "${BLUE}To restart the system:${NC}"
    echo "• Run: make up"
    echo "• Or: ./deploy/up.sh"
    echo ""

    if [ "$PRESERVE_DATA" = false ]; then
        echo -e "${YELLOW}Note: Since data was deleted, you'll need to run:${NC}"
        echo "• make init (to reinitialize)"
        echo "• make seed-data (to load test data)"
    fi
}

# Function to handle emergency shutdown
emergency_shutdown() {
    print_error "Emergency shutdown initiated!"
    print_status "Force stopping all containers..."

    # Force stop everything
    docker-compose -f "$DOCKER_COMPOSE_FILE" kill || true
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans || true

    print_warning "Emergency shutdown completed!"
}

# Main shutdown sequence
main() {
    cd "$PROJECT_ROOT"

    echo -e "${YELLOW}🛑 Shutting down Social Security AI System...${NC}"
    echo "======================================================="

    # Check if docker-compose file exists
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        print_error "docker-compose.yml file not found!"
        exit 1
    fi

    # Check if system is running
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
        print_warning "System doesn't appear to be running"
        if [ "$FORCE_SHUTDOWN" = false ]; then
            read -p "Continue with shutdown anyway? (y/N): " confirm
            if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                print_status "Shutdown cancelled"
                exit 0
            fi
        fi
    fi

    # Trap for emergency shutdown
    trap emergency_shutdown SIGINT SIGTERM

    # Create backup if requested
    create_backup

    # Save container logs before stopping
    save_container_logs

    # Stop services gracefully
    stop_services

    # Remove containers
    remove_containers

    # Clean volumes if requested
    clean_volumes

    # Clean networks
    clean_networks

    # Show final status
    show_final_status
}

# Parse arguments and run main function
parse_arguments "$@"
main