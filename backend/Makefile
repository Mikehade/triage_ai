
# Clinical Copilot API - Makefile


# Variables
DOCKER_IMAGE_NAME=clinical-copilot-api
DOCKER_IMAGE_TAG=latest
DOCKER_CONTAINER_NAME=clinal_copilot_app
DOCKER_COMPOSE_FILE=docker-compose.yml
DOCKER_NETWORK=clinical_copilot_network

# Colors for output
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
NC=\033[0m # No Color

.PHONY: help
help: ## Show this help message
	@echo '${BLUE}Clinical Copilot API - Available Commands:${NC}'
	@echo ''
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-20s${NC} %s\n", $$1, $$2}'
	@echo ''


# Docker Commands


.PHONY: build
build: ## Build Docker image
	@echo "${BLUE}Building Docker image...${NC}"
	docker build -t $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) .
	@echo "${GREEN}✓ Docker image built successfully${NC}"

.PHONY: build-no-cache
build-no-cache: ## Build Docker image without cache
	@echo "${BLUE}Building Docker image (no cache)...${NC}"
	docker build --no-cache -t $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) .
	@echo "${GREEN}✓ Docker image built successfully${NC}"

.PHONY: run
run: ## Run Docker container
	@echo "${BLUE}Starting Docker container...${NC}"
	docker run -d \
		--name $(DOCKER_CONTAINER_NAME) \
		-p 8000:8000 \
		-p 9001:9001 \
		--env-file .env \
		-v $(PWD)/logs:/app/logs \
		$(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)
	@echo "${GREEN}✓ Container started successfully${NC}"
	@echo "${YELLOW}API:        http://localhost:8000${NC}"
	@echo "${YELLOW}Supervisor: http://localhost:9001${NC}"

.PHONY: start
start: build run ## Build and run Docker container
	@echo "${GREEN}✓ Clinical Copilot API API is running!${NC}"

.PHONY: stop
stop: ## Stop Docker container
	@echo "${BLUE}Stopping Docker container...${NC}"
	docker stop $(DOCKER_CONTAINER_NAME) || true
	@echo "${GREEN}✓ Container stopped${NC}"

.PHONY: restart
restart: stop start ## Restart Docker container
	@echo "${GREEN}✓ Container restarted${NC}"

.PHONY: remove
remove: stop ## Remove Docker container
	@echo "${BLUE}Removing Docker container...${NC}"
	docker rm $(DOCKER_CONTAINER_NAME) || true
	@echo "${GREEN}✓ Container removed${NC}"

.PHONY: logs
logs: ## Show container logs
	docker logs -f $(DOCKER_CONTAINER_NAME)

.PHONY: shell
shell: ## Open shell in running container
	docker exec -it $(DOCKER_CONTAINER_NAME) /bin/bash

.PHONY: clean
clean: remove ## Clean up containers and images
	@echo "${BLUE}Cleaning up...${NC}"
	docker rmi $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) || true
	@echo "${GREEN}✓ Cleanup complete${NC}"


# Docker Compose Commands


.PHONY: up
up: ## Start all services with docker-compose
	@echo "${BLUE}Starting services with docker-compose...${NC}"
	docker-compose up -d
	@echo "${GREEN}✓ All services started${NC}"

.PHONY: down
down: ## Stop all services with docker-compose
	@echo "${BLUE}Stopping services...${NC}"
	docker-compose down
	@echo "${GREEN}✓ All services stopped${NC}"

.PHONY: ps
ps: ## Show running containers
	docker-compose ps

.PHONY: compose-logs
compose-logs: ## Show docker-compose logs
	docker-compose logs -f

.PHONY: compose-build
compose-build: ## Build with docker-compose
	docker-compose build


# Development Commands


.PHONY: dev
dev: ## Run in development mode (local)
	@echo "${BLUE}Starting development server...${NC}"
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

.PHONY: install
install: ## Install dependencies locally
	@echo "${BLUE}Installing dependencies...${NC}"
	pip install -r requirements.txt
	@echo "${GREEN}✓ Dependencies installed${NC}"

.PHONY: migrate
migrate: ## Run database migrations
	@echo "${BLUE}Running migrations...${NC}"
	alembic upgrade head
	@echo "${GREEN}✓ Migrations complete${NC}"

.PHONY: migrate-create
migrate-create: ## Create new migration (usage: make migrate-create msg="description")
	@echo "${BLUE}Creating migration...${NC}"
	alembic revision --autogenerate -m "$(msg)"
	@echo "${GREEN}✓ Migration created${NC}"


# Testing Commands


.PHONY: test
test: ## Run all tests
	@echo "${BLUE}Running tests...${NC}"
	pytest
	@echo "${GREEN}✓ Tests complete${NC}"

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "${BLUE}Running unit tests...${NC}"
	pytest tests/unit/
	@echo "${GREEN}✓ Unit tests complete${NC}"

.PHONY: test-cov
test-cov: ## Run tests with coverage
	@echo "${BLUE}Running tests with coverage...${NC}"
	pytest --cov=src --cov-report=html --cov-report=term
	@echo "${GREEN}✓ Coverage report generated${NC}"

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	@echo "${BLUE}Running tests in watch mode...${NC}"
	ptw


# Code Quality Commands


.PHONY: lint
lint: ## Run linting
	@echo "${BLUE}Running linters...${NC}"
	flake8 src tests
	@echo "${GREEN}✓ Linting complete${NC}"

.PHONY: format
format: ## Format code with black and isort
	@echo "${BLUE}Formatting code...${NC}"
	black src tests
	isort src tests
	@echo "${GREEN}✓ Code formatted${NC}"

.PHONY: format-check
format-check: ## Check code formatting
	@echo "${BLUE}Checking code format...${NC}"
	black --check src tests
	isort --check-only src tests
	@echo "${GREEN}✓ Code format OK${NC}"

.PHONY: type-check
type-check: ## Run type checking with mypy
	@echo "${BLUE}Running type checks...${NC}"
	mypy src
	@echo "${GREEN}✓ Type checking complete${NC}"

.PHONY: check-all
check-all: format-check lint type-check test ## Run all checks
	@echo "${GREEN}✓ All checks passed${NC}"


# Database Commands


.PHONY: db-shell
db-shell: ## Open PostgreSQL shell
	@echo "${BLUE}Opening database shell...${NC}"
	psql $(DATABASE_URL)

.PHONY: db-reset
db-reset: ## Reset database (WARNING: destroys data)
	@echo "${RED}⚠️  WARNING: This will destroy all data!${NC}"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		alembic downgrade base && alembic upgrade head; \
		echo "${GREEN}✓ Database reset complete${NC}"; \
	fi


# Utility Commands


.PHONY: create-network
create-network: ## Create Docker network
	docker network create $(DOCKER_NETWORK) || true

.PHONY: health
health: ## Check application health
	@curl -f http://localhost:8000/api/v1/health || echo "${RED}Health check failed${NC}"

.PHONY: supervisor-status
supervisor-status: ## Check supervisor status in container
	docker exec $(DOCKER_CONTAINER_NAME) supervisorctl status

.PHONY: supervisor-restart
supervisor-restart: ## Restart supervisor in container
	docker exec $(DOCKER_CONTAINER_NAME) supervisorctl restart all

.PHONY: supervisor-logs
supervisor-logs: ## View supervisor logs
	docker exec $(DOCKER_CONTAINER_NAME) tail -f /app/logs/supervisord.log

.PHONY: api-logs
api-logs: ## View API logs
	docker exec $(DOCKER_CONTAINER_NAME) tail -f /app/logs/api.log

.PHONY: celery-logs
celery-logs: ## View Celery worker logs
	docker exec $(DOCKER_CONTAINER_NAME) tail -f /app/logs/celery_worker.log

.PHONY: prune
prune: ## Remove unused Docker resources
	@echo "${BLUE}Pruning Docker resources...${NC}"
	docker system prune -f
	@echo "${GREEN}✓ Prune complete${NC}"


# Backup Commands


.PHONY: backup-db
backup-db: ## Backup database
	@echo "${BLUE}Backing up database...${NC}"
	@mkdir -p backups
	pg_dump $(DATABASE_URL) > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "${GREEN}✓ Database backed up${NC}"

.PHONY: restore-db
restore-db: ## Restore database (usage: make restore-db file=backup.sql)
	@echo "${BLUE}Restoring database from $(file)...${NC}"
	psql $(DATABASE_URL) < $(file)
	@echo "${GREEN}✓ Database restored${NC}"


# Documentation Commands


.PHONY: docs
docs: ## Generate API documentation
	@echo "${BLUE}API Documentation available at:${NC}"
	@echo "${YELLOW}http://localhost:8000/docs${NC}"
	@echo "${YELLOW}http://localhost:8000/redoc${NC}"

# Default target
.DEFAULT_GOAL := help