.PHONY: up down restart logs logs-web logs-worker logs-beat logs-flower logs-db logs-redis \
		build rebuild clean ps shell-web shell-worker shell-beat shell-flower shell-db shell-redis \
		init-db migrate migrate-up migrate-down test lint

# Docker Compose commands
up:
	docker compose up -d

debug-run:
	docker compose -f docker-compose.yaml -f docker-compose.debug.yaml up

debug-down:
	docker compose -f docker-compose.yaml -f docker-compose.debug.yaml down
	
down:
	docker compose down

restart:
	docker compose restart

# Logs
logs:
	docker compose logs -f

logs-web:
	docker compose logs -f web

logs-worker:
	docker compose logs -f celery_worker

logs-beat:
	docker compose logs -f celery_beat

logs-flower:
	docker compose logs -f flower

logs-db:
	docker compose logs -f db

logs-redis:
	docker compose logs -f redis

# Build commands
build:
	docker compose build

rebuild:
	docker compose build --no-cache

clean:
	docker compose down -v
	docker system prune -f

# Container status
ps:
	docker compose ps

# Shell access
shell-web:
	docker compose exec web bash

shell-worker:
	docker compose exec celery_worker bash

shell-beat:
	docker compose exec celery_beat bash

shell-flower:
	docker compose exec flower bash

shell-db:
	docker compose exec db psql -U whispercore

shell-redis:
	docker compose exec redis redis-cli

# Database commands
init-db:
	docker compose exec web flask db init

migration-create:
	docker compose exec web flask db migrate --rev-id "$(rev)"

migrate:
	docker compose exec web flask db migrate

migrate-up:
	docker compose exec web flask db upgrade

migrate-down:
	docker compose exec web flask db downgrade

reset-db:
	@echo "Stopping and removing all containers and volumes..."
	docker compose down -v
	@echo "Removing old migration history..."
	rm -rf migrations
	@echo "Starting services..."
	docker compose up --build -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Initializing new migration history..."
	docker compose exec web flask db init
	@echo "Generating initial migration..."
	docker compose exec web flask db migrate -m "Initial migration"
	@echo "Applying new migration..."
	docker compose exec web flask db upgrade
	@echo "Database has been reset successfully."
# Development commands
test:
	@echo "Running all tests..."
	pytest tests/ -v --tb=short

test-target:
	@echo "Running tests for $(TARGET)"
	pytest $(TARGET) -v --tb=short

lint:
	docker compose exec web flake8

# Help command
help:
	@echo "Available commands:"
	@echo "  up              - Start all containers"
	@echo "  down            - Stop all containers"
	@echo "  restart         - Restart all containers"
	@echo "  logs            - View all container logs"
	@echo "  logs-web        - View web container logs"
	@echo "  logs-worker     - View worker container logs"
	@echo "  logs-beat       - View beat container logs"
	@echo "  logs-flower     - View flower container logs"
	@echo "  logs-db         - View database container logs"
	@echo "  logs-redis      - View redis container logs"
	@echo "  build           - Build all containers"
	@echo "  rebuild         - Rebuild all containers without cache"
	@echo "  clean           - Remove all containers and volumes"
	@echo "  ps              - Show container status"
	@echo "  shell-web       - Open shell in web container"
	@echo "  shell-worker    - Open shell in worker container"
	@echo "  shell-beat      - Open shell in beat container"
	@echo "  shell-flower    - Open shell in flower container"
	@echo "  shell-db        - Open PostgreSQL shell"
	@echo "  shell-redis     - Open Redis CLI"
	@echo "  init-db         - Initialize database"
	@echo "  migrate         - Create new migration"
	@echo "  migrate-up      - Apply migrations"
	@echo "  migrate-down    - Rollback migrations"
	@echo "  reset-db        - Reset the database"
	@echo "  test            - Run tests"
	@echo "  lint            - Run linter"
	@echo "  help            - Show this help message" 