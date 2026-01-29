.PHONY: help docker-up docker-down docker-restart docker-logs install migrate seed dev build clean

# Variables
COMPOSE_FILE=docker-compose.yml
COMPOSE_MINIMAL=docker-compose.minimal.yml

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Docker Commands
docker-up: ## Start all Docker services
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "✅ Docker services started!"
	@echo "   PostgreSQL: localhost:5433"
	@echo "   pgAdmin: http://localhost:5050"
	@echo "   Redis: localhost:6379"
	@echo "   Mailhog: http://localhost:8025"

docker-up-minimal: ## Start only PostgreSQL
	docker-compose -f $(COMPOSE_MINIMAL) up -d
	@echo "✅ PostgreSQL started on localhost:5433"

docker-down: ## Stop all Docker services
	docker-compose -f $(COMPOSE_FILE) down
	@echo "✅ Docker services stopped"

docker-down-clean: ## Stop services and remove volumes (⚠️  deletes data!)
	@echo "⚠️  This will delete all data in the database!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose -f $(COMPOSE_FILE) down -v; \
		echo "✅ Docker services and volumes removed"; \
	fi

docker-restart: ## Restart all Docker services
	docker-compose -f $(COMPOSE_FILE) restart
	@echo "✅ Docker services restarted"

docker-logs: ## Show logs from all services
	docker-compose -f $(COMPOSE_FILE) logs -f

docker-logs-db: ## Show PostgreSQL logs
	docker-compose -f $(COMPOSE_FILE) logs -f postgres

docker-ps: ## Show running Docker services
	docker-compose -f $(COMPOSE_FILE) ps

# Database Commands
db-cli: ## Access PostgreSQL CLI
	docker exec -it mbt_postgres psql -U mbt_user -d mybustimes_v3

db-backup: ## Backup database to backup.sql
	docker exec mbt_postgres pg_dump -U mbt_user mybustimes_v3 > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backed up"

db-restore: ## Restore database from backup.sql (requires backup.sql file)
	@if [ ! -f backup.sql ]; then \
		echo "❌ backup.sql not found"; \
		exit 1; \
	fi
	docker exec -i mbt_postgres psql -U mbt_user -d mybustimes_v3 < backup.sql
	@echo "✅ Database restored"

# Application Commands
install: ## Install dependencies
	npm install
	@echo "✅ Dependencies installed"

setup: ## Full setup (Docker + install + migrate)
	make docker-up
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 5
	make install
	npx prisma generate
	make migrate
	@echo "✅ Setup complete! Run 'make dev' to start developing"

migrate: ## Run Prisma migrations
	npx prisma migrate dev
	@echo "✅ Migrations complete"

migrate-create: ## Create a new migration (use name=your_migration_name)
	npx prisma migrate dev --name $(name)

seed: ## Seed the database
	npm run prisma:seed
	@echo "✅ Database seeded"

generate: ## Generate Prisma Client
	npx prisma generate
	@echo "✅ Prisma Client generated"

studio: ## Open Prisma Studio
	npx prisma studio

# Development Commands
dev: ## Start Next.js development server
	npm run dev

build: ## Build for production
	npm run build

start: ## Start production server
	npm run start

lint: ## Run ESLint
	npm run lint

format: ## Format code with Prettier
	npx prettier --write .

# Cleanup Commands
clean: ## Clean node_modules and build files
	rm -rf node_modules .next
	@echo "✅ Cleaned node_modules and .next"

reset: ## Full reset (⚠️  deletes everything!)
	@echo "⚠️  This will delete all data and dependencies!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		make docker-down-clean; \
		make clean; \
		echo "✅ Full reset complete"; \
	fi

# Quick start commands
first-time: ## First time setup (run this once)
	@echo "🚀 Running first-time setup..."
	@if [ ! -f .env ]; then \
		cp .env.docker .env; \
		echo "📝 Created .env file - please update NEXTAUTH_SECRET"; \
		echo "   Generate with: openssl rand -base64 32"; \
		exit 1; \
	fi
	make setup
	@echo "✨ All done! Run 'make dev' to start developing"

quick-start: ## Quick start (after first-time setup)
	make docker-up
	@sleep 3
	make dev