.PHONY: setup dev build down test lint format clean help

# Default environment configuration
ENV_FILE ?= .env

help:
	@echo "=============================================================================="
	@echo "NOTED MA'AM DEV CLI"
	@echo "=============================================================================="
	@echo "make setup      - Copy .env.example, run basic local configurations"
	@echo "make dev        - Launch backing services (DB, Redis, MinIO) and local backend/frontend"
	@echo "make build      - Build all docker containers from source"
	@echo "make down       - Tear down local containers and network bindings"
	@echo "make test       - Execute python backend tests and frontend validation suites"
	@echo "make lint       - Run static analysis lint checks (Ruff, ESLint, Prettier)"
	@echo "make format     - Automatically format Python/JS/TS source code"
	@echo "make clean      - Clean cache artifacts, node modules, build targets"

setup:
	@echo "Initializing workspace configurations..."
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env file created from template."; fi
	@if [ ! -f backend/.env ]; then cp .env.example backend/.env; fi
	@if [ ! -f frontend/.env ]; then cp .env.example frontend/.env; fi
	@echo "Monorepo configuration complete. Run 'make dev' to start all services."

dev:
	@echo "Launching backing services and development runtime via Docker Compose..."
	docker compose --env-file $(ENV_FILE) up --build

build:
	@echo "Rebuilding image layers..."
	docker compose build

down:
	@echo "Stopping backing containers..."
	docker compose down -v

lint:
	@echo "Running Ruff linter on Python backend..."
	cd backend && poetry run ruff check . || pip install ruff && ruff check .
	@echo "Running lint on frontend..."
	cd frontend && npm run lint

format:
	@echo "Running Ruff code formatting..."
	cd backend && poetry run ruff format . || ruff format .
	@echo "Running Prettier on frontend..."
	cd frontend && npm run format

test:
	@echo "Running backend test suite (pytest)..."
	cd backend && poetry run pytest || pytest
	@echo "Running frontend test suite (vitest)..."
	cd frontend && npm run test

clean:
	@echo "Cleaning workspace targets..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".next" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
