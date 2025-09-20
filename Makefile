# Makefile for Social Security AI System
# Master control file for deployment, testing, and operations

.PHONY: help install build up down init logs clean test test-unit test-integration test-e2e verify health status restart

# Default target
.DEFAULT_GOAL := help

# Variables
DOCKER_COMPOSE = docker compose
PYTHON = python3
PIP = pip3
PYTEST = pytest
PROJECT_NAME = social-security-ai

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)Social Security AI System - Available Commands$(NC)"
	@echo "=================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install system dependencies and requirements
	@echo "$(GREEN)Installing system dependencies...$(NC)"
	@chmod +x deploy/*.sh scripts/*.py
	@$(PIP) install -r requirements.txt
	@echo "$(GREEN)Dependencies installed successfully!$(NC)"

build: ## Build Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	@$(DOCKER_COMPOSE) build --no-cache
	@echo "$(GREEN)Docker images built successfully!$(NC)"

pull: ## Pull required Docker images
	@echo "$(GREEN)Pulling Docker images...$(NC)"
	@$(DOCKER_COMPOSE) pull postgres redis qdrant ollama
	@echo "$(GREEN)Docker images pulled successfully!$(NC)"

init: ## Initialize the complete system (first-time setup)
	@echo "$(GREEN)Initializing Social Security AI System...$(NC)"
	@./deploy/init.sh
	@echo "$(GREEN)System initialization completed!$(NC)"

up: ## Start all services
	@echo "$(GREEN)Starting all services...$(NC)"
	@./deploy/up.sh
	@echo "$(GREEN)All services started successfully!$(NC)"

down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	@./deploy/down.sh
	@echo "$(GREEN)All services stopped successfully!$(NC)"

restart: ## Restart all services
	@echo "$(YELLOW)Restarting all services...$(NC)"
	@make down
	@sleep 5
	@make up

status: ## Show status of all services
	@echo "$(GREEN)Service Status:$(NC)"
	@$(DOCKER_COMPOSE) ps
	@echo "\n$(GREEN)Container Health:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

health: ## Run health checks on all services
	@echo "$(GREEN)Running health checks...$(NC)"
	@./deploy/docker_health.sh

logs: ## View logs from all services
	@echo "$(GREEN)Viewing system logs...$(NC)"
	@$(DOCKER_COMPOSE) logs -f --tail=100

logs-api: ## View FastAPI logs
	@$(DOCKER_COMPOSE) logs -f fastapi-app

logs-worker: ## View Celery worker logs
	@$(DOCKER_COMPOSE) logs -f celery-worker

logs-frontend: ## View Streamlit frontend logs
	@$(DOCKER_COMPOSE) logs -f streamlit-frontend

logs-db: ## View database logs
	@$(DOCKER_COMPOSE) logs -f postgres

verify: ## Verify all system modules are working
	@echo "$(GREEN)Verifying system functionality...$(NC)"
	@$(PYTHON) scripts/verify_system.py
	@echo "$(GREEN)System verification completed!$(NC)"

test: test-unit test-integration ## Run all tests

test-unit: ## Run unit tests
	@echo "$(GREEN)Running unit tests...$(NC)"
	@$(PYTEST) tests/unit/ -v --tb=short

test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	@$(PYTEST) tests/integration/ -v --tb=short

test-e2e: ## Run end-to-end tests
	@echo "$(GREEN)Running end-to-end tests...$(NC)"
	@$(PYTEST) tests/e2e/ -v --tb=short

test-load: ## Run load tests
	@echo "$(GREEN)Running load tests...$(NC)"
	@$(PYTHON) tests/load/load_test.py

test-auth: ## Test authentication flow specifically
	@echo "$(GREEN)Testing authentication flow...$(NC)"
	@$(PYTEST) tests/integration/test_auth.py -v

test-docs: ## Test document processing flow
	@echo "$(GREEN)Testing document processing...$(NC)"
	@$(PYTEST) tests/integration/test_document_flow.py -v

test-decisions: ## Test decision making flow
	@echo "$(GREEN)Testing decision making...$(NC)"
	@$(PYTEST) tests/integration/test_decision_flow.py -v

seed-data: ## Load test data into the system
	@echo "$(GREEN)Loading test data...$(NC)"
	@$(PYTHON) scripts/seed_users.py
	@$(PYTHON) scripts/generate_test_data.py
	@echo "$(GREEN)Test data loaded successfully!$(NC)"

reset: ## Reset the entire system (WARNING: destroys all data)
	@echo "$(RED)WARNING: This will destroy all data!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	@$(PYTHON) scripts/reset_system.py
	@echo "$(GREEN)System reset completed!$(NC)"

clean: ## Clean up containers, volumes, and images
	@echo "$(YELLOW)Cleaning up Docker resources...$(NC)"
	@$(DOCKER_COMPOSE) down -v --remove-orphans
	@docker system prune -f
	@echo "$(GREEN)Cleanup completed!$(NC)"

clean-all: ## Clean everything including images (NUCLEAR OPTION)
	@echo "$(RED)WARNING: This will remove all Docker images!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	@$(DOCKER_COMPOSE) down -v --rmi all --remove-orphans
	@docker system prune -af --volumes
	@echo "$(GREEN)Complete cleanup finished!$(NC)"

shell-api: ## Open shell in FastAPI container
	@$(DOCKER_COMPOSE) exec fastapi-app /bin/bash

shell-worker: ## Open shell in Celery worker container
	@$(DOCKER_COMPOSE) exec celery-worker /bin/bash

shell-db: ## Open PostgreSQL shell
	@$(DOCKER_COMPOSE) exec postgres psql -U admin -d social_security_ai

shell-redis: ## Open Redis shell
	@$(DOCKER_COMPOSE) exec redis redis-cli

dev-setup: install build init up seed-data verify ## Complete development setup

production-setup: ## Setup for production deployment
	@echo "$(GREEN)Setting up production environment...$(NC)"
	@cp .env .env.backup
	@echo "Please update .env with production values before continuing"
	@echo "Run 'make init && make up' when ready"

backup: ## Backup database and uploaded files
	@echo "$(GREEN)Creating system backup...$(NC)"
	@mkdir -p backups
	@$(DOCKER_COMPOSE) exec postgres pg_dump -U admin social_security_ai > backups/db_backup_$(shell date +%Y%m%d_%H%M%S).sql
	@tar -czf backups/uploads_backup_$(shell date +%Y%m%d_%H%M%S).tar.gz uploads/
	@echo "$(GREEN)Backup completed!$(NC)"

monitor: ## Monitor system metrics
	@echo "$(GREEN)Monitoring system metrics...$(NC)"
	@watch -n 2 "docker stats --no-stream && echo '' && docker-compose ps"

# Quick commands for common workflows
quick-start: build up verify ## Quick start for development
quick-test: test-unit test-auth ## Quick test suite
quick-restart: down up verify ## Quick restart with verification

# Development helpers
format: ## Format Python code
	@black app/ tests/ scripts/ frontend/
	@isort app/ tests/ scripts/ frontend/

lint: ## Run code linting
	@flake8 app/ tests/ scripts/ frontend/
	@mypy app/

security-scan: ## Run security scan
	@bandit -r app/
	@safety check

docs: ## Generate API documentation
	@echo "API documentation available at http://localhost:8000/docs when system is running"

# Troubleshooting
debug-api: ## Debug API issues
	@echo "$(GREEN)API Debug Information:$(NC)"
	@curl -f http://localhost:8000/health || echo "API not responding"
	@$(DOCKER_COMPOSE) logs --tail=50 fastapi-app

debug-worker: ## Debug worker issues
	@echo "$(GREEN)Worker Debug Information:$(NC)"
	@$(DOCKER_COMPOSE) logs --tail=50 celery-worker

debug-db: ## Debug database issues
	@echo "$(GREEN)Database Debug Information:$(NC)"
	@$(DOCKER_COMPOSE) exec postgres pg_isready -U admin
	@$(DOCKER_COMPOSE) logs --tail=20 postgres

debug-ollama: ## Debug Ollama AI service
	@echo "$(GREEN)Ollama Debug Information:$(NC)"
	@curl -f http://localhost:11434/api/tags || echo "Ollama not responding"
	@$(DOCKER_COMPOSE) logs --tail=20 ollama

# Performance testing
perf-test: ## Run performance benchmarks
	@echo "$(GREEN)Running performance tests...$(NC)"
	@$(PYTHON) scripts/performance_test.py

# Show system information
info: ## Show system information
	@echo "$(GREEN)Social Security AI System Information$(NC)"
	@echo "======================================"
	@echo "Project: $(PROJECT_NAME)"
	@echo "Docker Compose: $(shell docker-compose --version)"
	@echo "Python: $(shell python3 --version)"
	@echo "Current directory: $(shell pwd)"
	@echo "Environment: $(shell grep ENVIRONMENT .env | cut -d'=' -f2)"
	@echo ""
	@echo "$(GREEN)Available Services:$(NC)"
	@echo "- API Server: http://localhost:8000"
	@echo "- Dashboard: http://localhost:8005"
	@echo "- Database: localhost:5432"
	@echo "- Redis: localhost:6379"
	@echo "- Qdrant: http://localhost:6333"
	@echo "- Ollama: http://localhost:11434"