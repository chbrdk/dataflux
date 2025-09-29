# DataFlux Makefile

.PHONY: help
help:
	@echo "DataFlux Development Commands"
	@echo "=============================="
	@echo "make setup       - Initial setup"
	@echo "make dev         - Start development environment"
	@echo "make dev-tools   - Start with development tools"
	@echo "make stop        - Stop all services"
	@echo "make clean       - Clean up volumes and containers"
	@echo "make logs        - Show logs"
	@echo "make test        - Run tests"
	@echo "make build       - Build all services"
	@echo "make migrate     - Run database migrations"
	@echo "make shell       - Open shell in service"
	@echo "make psql        - Connect to PostgreSQL"
	@echo "make redis-cli   - Connect to Redis"

.PHONY: setup
setup:
	@echo "Setting up DataFlux development environment..."
	@cp docker/.env.example docker/.env
	@echo "Please edit docker/.env with your configuration"
	@docker network create dataflux-network 2>/dev/null || true
	@make build
	@make migrate

.PHONY: dev
dev:
	@cd docker && docker-compose up -d
	@echo "DataFlux is running!"
	@echo "API Gateway: http://localhost"
	@echo "API Docs: http://localhost/docs"

.PHONY: dev-tools
dev-tools:
	@cd docker && docker-compose --profile dev --profile tools up -d
	@echo "Development tools are running!"
	@echo "PgAdmin: http://localhost:5050"
	@echo "Kafka UI: http://localhost:8090"
	@echo "Redis Commander: http://localhost:8081"
	@echo "MinIO Console: http://localhost:9001"

.PHONY: stop
stop:
	@cd docker && docker-compose stop

.PHONY: clean
clean:
	@cd docker && docker-compose down -v
	@docker network rm dataflux-network 2>/dev/null || true

.PHONY: logs
logs:
	@cd docker && docker-compose logs -f

.PHONY: logs-service
logs-service:
	@cd docker && docker-compose logs -f $(SERVICE)

.PHONY: test
test:
	@echo "Running tests..."
	@cd services/ingestion-service && python -m pytest
	@cd services/query-service && go test ./...
	@cd services/mcp-server && npm test

.PHONY: build
build:
	@cd docker && docker-compose build

.PHONY: migrate
migrate:
	@cd docker && docker-compose run --rm postgres psql -h postgres -U dataflux_user -d dataflux -f /docker-entrypoint-initdb.d/01-init.sql

.PHONY: shell
shell:
	@cd docker && docker-compose exec $(SERVICE) /bin/sh

.PHONY: psql
psql:
	@cd docker && docker-compose exec postgres psql -U dataflux_user -d dataflux

.PHONY: redis-cli
redis-cli:
	@cd docker && docker-compose exec redis redis-cli -a dataflux_pass

.PHONY: status
status:
	@cd docker && docker-compose ps

.PHONY: restart
restart:
	@cd docker && docker-compose restart $(SERVICE)

.PHONY: rebuild
rebuild:
	@cd docker && docker-compose build --no-cache $(SERVICE)
	@cd docker && docker-compose up -d $(SERVICE)
