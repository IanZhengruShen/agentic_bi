.PHONY: help build up down restart logs clean test lint format db-migrate db-reset

# Default target
help:
	@echo "Agentic BI Platform - Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup              - Initial project setup"
	@echo "  make env                - Copy .env.example to .env"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make build              - Build all Docker images"
	@echo "  make up                 - Start all services"
	@echo "  make down               - Stop all services"
	@echo "  make restart            - Restart all services"
	@echo "  make logs               - View logs from all services"
	@echo "  make logs-backend       - View backend logs"
	@echo "  make logs-frontend      - View frontend logs"
	@echo "  make ps                 - Show running containers"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-shell           - Access PostgreSQL shell"
	@echo "  make db-migrate         - Run database migrations"
	@echo "  make db-reset           - Reset database (WARNING: deletes data)"
	@echo ""
	@echo "Development Commands:"
	@echo "  make backend-shell      - Access backend container shell"
	@echo "  make frontend-shell     - Access frontend container shell"
	@echo "  make test               - Run all tests"
	@echo "  make test-backend       - Run backend tests"
	@echo "  make test-frontend      - Run frontend tests"
	@echo "  make lint               - Run linters"
	@echo "  make format             - Format code"
	@echo ""
	@echo "Cleanup Commands:"
	@echo "  make clean              - Remove containers, volumes, and networks"
	@echo "  make clean-all          - Remove everything including images"
	@echo ""

# ============================================
# Setup Commands
# ============================================

setup: env build
	@echo "✓ Project setup complete!"
	@echo "Next steps:"
	@echo "  1. Edit .env file with your configuration"
	@echo "  2. Run 'make up' to start services"

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env file from .env.example"; \
		echo "⚠ Please edit .env with your configuration"; \
	else \
		echo "✓ .env file already exists"; \
	fi

# ============================================
# Docker Commands
# ============================================

build:
	@echo "Building Docker images..."
	docker-compose build

up:
	@echo "Starting services..."
	docker-compose up -d
	@echo "✓ Services started"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "API Docs: http://localhost:8000/docs"

down:
	@echo "Stopping services..."
	docker-compose down

restart:
	@echo "Restarting services..."
	docker-compose restart

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-celery:
	docker-compose logs -f celery-worker

ps:
	docker-compose ps

# ============================================
# Database Commands
# ============================================

db-shell:
	docker-compose exec postgres psql -U $${POSTGRES_USER:-admin} -d $${POSTGRES_DB:-agentic_bi}

db-migrate:
	docker-compose exec backend alembic upgrade head

db-reset:
	@echo "⚠ WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker-compose up -d postgres; \
		sleep 5; \
		docker-compose up -d; \
		echo "✓ Database reset complete"; \
	fi

# ============================================
# Development Commands
# ============================================

backend-shell:
	docker-compose exec backend /bin/bash

frontend-shell:
	docker-compose exec frontend /bin/sh

redis-cli:
	docker-compose exec redis redis-cli -a $${REDIS_PASSWORD:-devredispass}

# ============================================
# Testing Commands
# ============================================

test: test-backend test-frontend

test-backend:
	@echo "Running backend tests..."
	docker-compose exec backend pytest tests/ -v

test-frontend:
	@echo "Running frontend tests..."
	docker-compose exec frontend npm test

test-coverage:
	@echo "Running tests with coverage..."
	docker-compose exec backend pytest tests/ --cov=app --cov-report=html

# ============================================
# Code Quality Commands
# ============================================

lint: lint-backend lint-frontend

lint-backend:
	@echo "Linting backend code..."
	docker-compose exec backend flake8 app/
	docker-compose exec backend black --check app/
	docker-compose exec backend isort --check-only app/

lint-frontend:
	@echo "Linting frontend code..."
	docker-compose exec frontend npm run lint

format: format-backend format-frontend

format-backend:
	@echo "Formatting backend code..."
	docker-compose exec backend black app/
	docker-compose exec backend isort app/

format-frontend:
	@echo "Formatting frontend code..."
	docker-compose exec frontend npm run format

# ============================================
# Cleanup Commands
# ============================================

clean:
	@echo "Cleaning up containers, volumes, and networks..."
	docker-compose down -v
	@echo "✓ Cleanup complete"

clean-all:
	@echo "⚠ WARNING: This will remove all containers, volumes, networks, and images!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --rmi all; \
		echo "✓ Complete cleanup done"; \
	fi

# ============================================
# Monitoring Commands
# ============================================

stats:
	docker stats $$(docker-compose ps -q)

health:
	@echo "Checking service health..."
	@docker-compose ps

# ============================================
# Production Commands
# ============================================

prod-build:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

prod-up:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
