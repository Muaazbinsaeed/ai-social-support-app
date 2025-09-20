#!/bin/bash

# Social Security AI System - Docker Health Monitoring Script
# This script monitors container health, resource usage, and connectivity

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# Command line options
CONTINUOUS_MODE=false
DETAILED_MODE=false
EXPORT_METRICS=false
INTERVAL=30

echo -e "${PURPLE}🏥 Social Security AI System - Health Monitor${NC}"
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
    echo -e "\n${CYAN}=== $1 ===${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -c, --continuous    Run in continuous monitoring mode"
    echo "  -d, --detailed      Show detailed metrics"
    echo "  -e, --export        Export metrics to file"
    echo "  -i, --interval N    Set monitoring interval (default: 30s)"
    echo ""
    echo "Examples:"
    echo "  $0                  Single health check"
    echo "  $0 -c               Continuous monitoring"
    echo "  $0 -d -e            Detailed check with export"
    echo "  $0 -c -i 60         Continuous with 60s interval"
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -c|--continuous)
                CONTINUOUS_MODE=true
                shift
                ;;
            -d|--detailed)
                DETAILED_MODE=true
                shift
                ;;
            -e|--export)
                EXPORT_METRICS=true
                shift
                ;;
            -i|--interval)
                INTERVAL="$2"
                shift 2
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Function to check if container is running
check_container_status() {
    local service_name=$1
    local container_id=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q "$service_name" 2>/dev/null)

    if [ -z "$container_id" ]; then
        echo "❌ Not running"
        return 1
    fi

    local status=$(docker inspect "$container_id" --format='{{.State.Status}}' 2>/dev/null)
    local health=$(docker inspect "$container_id" --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-healthcheck")

    case $status in
        "running")
            if [ "$health" = "healthy" ]; then
                echo "✅ Running (Healthy)"
            elif [ "$health" = "unhealthy" ]; then
                echo "⚠️ Running (Unhealthy)"
            elif [ "$health" = "starting" ]; then
                echo "🔄 Running (Starting)"
            else
                echo "✅ Running"
            fi
            return 0
            ;;
        "exited")
            echo "❌ Exited"
            return 1
            ;;
        "restarting")
            echo "🔄 Restarting"
            return 1
            ;;
        *)
            echo "❓ $status"
            return 1
            ;;
    esac
}

# Function to check container resource usage
check_container_resources() {
    local service_name=$1
    local container_id=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q "$service_name" 2>/dev/null)

    if [ -z "$container_id" ]; then
        echo "N/A"
        return 1
    fi

    # Get resource stats
    local stats=$(docker stats "$container_id" --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null)

    if [ $? -eq 0 ]; then
        echo "$stats" | tail -n +2
    else
        echo "N/A"
        return 1
    fi
}

# Function to test service connectivity
test_service_connectivity() {
    local service_name=$1
    local endpoint=$2
    local expected_response=$3

    if curl -f -s -m 10 "$endpoint" > /dev/null 2>&1; then
        echo "✅ Accessible"
        return 0
    else
        echo "❌ Not accessible"
        return 1
    fi
}

# Function to check port availability
check_port_status() {
    local port=$1
    local service_name=$2

    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo "✅ Port $port (${service_name})"
        return 0
    else
        echo "❌ Port $port (${service_name})"
        return 1
    fi
}

# Function to check database connectivity
check_database_connectivity() {
    local container_id=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q postgres 2>/dev/null)

    if [ -z "$container_id" ]; then
        echo "❌ Container not running"
        return 1
    fi

    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres pg_isready -U admin >/dev/null 2>&1; then
        echo "✅ Database responsive"

        # Check database size if detailed mode
        if [ "$DETAILED_MODE" = true ]; then
            local db_size=$(docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres psql -U admin -d social_security_ai -t -c "SELECT pg_size_pretty(pg_database_size('social_security_ai'));" 2>/dev/null | xargs)
            echo "   Database size: $db_size"
        fi

        return 0
    else
        echo "❌ Database not responding"
        return 1
    fi
}

# Function to check Redis connectivity
check_redis_connectivity() {
    local container_id=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q redis 2>/dev/null)

    if [ -z "$container_id" ]; then
        echo "❌ Container not running"
        return 1
    fi

    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
        echo "✅ Redis responsive"

        # Check Redis memory usage if detailed mode
        if [ "$DETAILED_MODE" = true ]; then
            local memory_info=$(docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T redis redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')
            echo "   Memory usage: $memory_info"
        fi

        return 0
    else
        echo "❌ Redis not responding"
        return 1
    fi
}

# Function to check Ollama models
check_ollama_models() {
    if curl -f -s "http://localhost:11434/api/tags" > /dev/null 2>&1; then
        local models=$(curl -s "http://localhost:11434/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | wc -l)
        echo "✅ Ollama responsive ($models models)"

        if [ "$DETAILED_MODE" = true ]; then
            echo "   Available models:"
            curl -s "http://localhost:11434/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | sed 's/^/     - /'
        fi

        return 0
    else
        echo "❌ Ollama not responding"
        return 1
    fi
}

# Function to check API endpoints
check_api_endpoints() {
    local base_url="http://localhost:8000"
    local endpoints=(
        "$base_url/health:Health"
        "$base_url/docs:Documentation"
        "$base_url/auth/login:Authentication"
    )

    echo "API Endpoints:"
    for endpoint_info in "${endpoints[@]}"; do
        local endpoint=$(echo "$endpoint_info" | cut -d: -f1)
        local name=$(echo "$endpoint_info" | cut -d: -f2)

        if curl -f -s -m 5 "$endpoint" > /dev/null 2>&1; then
            echo "   ✅ $name"
        else
            echo "   ❌ $name"
        fi
    done
}

# Function to check disk usage
check_disk_usage() {
    echo "Disk Usage:"

    # Check main project directory
    local project_size=$(du -sh "$PROJECT_ROOT" 2>/dev/null | cut -f1)
    echo "   Project size: $project_size"

    # Check uploads directory
    if [ -d "$PROJECT_ROOT/uploads" ]; then
        local uploads_size=$(du -sh "$PROJECT_ROOT/uploads" 2>/dev/null | cut -f1)
        echo "   Uploads: $uploads_size"
    fi

    # Check logs directory
    if [ -d "$PROJECT_ROOT/logs" ]; then
        local logs_size=$(du -sh "$PROJECT_ROOT/logs" 2>/dev/null | cut -f1)
        echo "   Logs: $logs_size"
    fi

    # Check Docker volumes
    echo "   Docker volumes:"
    docker volume ls --format "table {{.Name}}\t{{.Size}}" 2>/dev/null | grep social-security || echo "     No volumes found"
}

# Function to check network connectivity
check_network_connectivity() {
    echo "Network Connectivity:"

    # Check internal network
    local network_name=$(docker-compose -f "$DOCKER_COMPOSE_FILE" config | grep "name:" | head -1 | awk '{print $2}')
    if docker network inspect "$network_name" >/dev/null 2>&1; then
        echo "   ✅ Internal network ($network_name)"
    else
        echo "   ❌ Internal network"
    fi

    # Check external connectivity
    if curl -f -s -m 5 "https://httpbin.org/status/200" > /dev/null 2>&1; then
        echo "   ✅ External connectivity"
    else
        echo "   ❌ External connectivity"
    fi
}

# Function to export metrics
export_metrics() {
    if [ "$EXPORT_METRICS" = true ]; then
        local timestamp=$(date +"%Y%m%d_%H%M%S")
        local export_file="$PROJECT_ROOT/logs/health_metrics_$timestamp.json"

        mkdir -p "$PROJECT_ROOT/logs"

        echo "Exporting metrics to $export_file..."

        # Create JSON metrics
        cat > "$export_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "system": {
        "containers": $(docker-compose -f "$DOCKER_COMPOSE_FILE" ps --format json 2>/dev/null || echo "[]"),
        "stats": $(docker stats --no-stream --format json 2>/dev/null | jq -s '.' || echo "[]")
    }
}
EOF

        print_success "Metrics exported to $export_file"
    fi
}

# Function to perform comprehensive health check
perform_health_check() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo -e "\n${PURPLE}🏥 Health Check - $timestamp${NC}"
    echo "============================================================="

    # Container Status
    print_header "Container Status"
    local services=("fastapi-app" "celery-worker" "streamlit-frontend" "postgres" "redis" "qdrant" "ollama")

    for service in "${services[@]}"; do
        printf "%-20s " "$service:"
        check_container_status "$service"
    done

    # Port Status
    print_header "Port Status"
    local ports=(
        "8000:API"
        "8005:Frontend"
        "5432:PostgreSQL"
        "6379:Redis"
        "6333:Qdrant"
        "11434:Ollama"
    )

    for port_info in "${ports[@]}"; do
        local port=$(echo "$port_info" | cut -d: -f1)
        local service=$(echo "$port_info" | cut -d: -f2)
        check_port_status "$port" "$service"
    done

    # Service Connectivity
    print_header "Service Connectivity"
    printf "%-20s " "Database:"
    check_database_connectivity

    printf "%-20s " "Redis:"
    check_redis_connectivity

    printf "%-20s " "Ollama AI:"
    check_ollama_models

    # API Health
    print_header "API Health"
    check_api_endpoints

    # Resource Usage (if detailed mode)
    if [ "$DETAILED_MODE" = true ]; then
        print_header "Resource Usage"

        echo "Container Resources:"
        for service in "${services[@]}"; do
            printf "   %-15s " "$service:"
            check_container_resources "$service"
        done

        print_header "System Resources"
        check_disk_usage
        check_network_connectivity
    fi

    # Export metrics if requested
    export_metrics

    echo -e "\n${GREEN}Health check completed!${NC}"
}

# Function for continuous monitoring
continuous_monitoring() {
    print_status "Starting continuous monitoring (interval: ${INTERVAL}s)"
    print_status "Press Ctrl+C to stop"

    while true; do
        clear
        perform_health_check
        sleep "$INTERVAL"
    done
}

# Main function
main() {
    cd "$PROJECT_ROOT"

    # Check if docker-compose file exists
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        print_error "docker-compose.yml file not found!"
        exit 1
    fi

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running!"
        exit 1
    fi

    if [ "$CONTINUOUS_MODE" = true ]; then
        continuous_monitoring
    else
        perform_health_check
    fi
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Monitoring stopped by user${NC}"; exit 0' SIGINT

# Parse arguments and run main function
parse_arguments "$@"
main