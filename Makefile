# Variables
COMPOSE_DIR := deployment
COMPOSE_FILE := docker-compose.yaml
DEV_COMPOSE_FILE := docker-compose.dev.yaml

.PHONY: help init infra dev prod down clean status

help:
	@echo "Smart Scheduler Management Commands:"
	@echo "  make infra    - Start infrastructure only (DB + VectorDB) for local dev"
	@echo "                  Frontend: npm run dev → http://localhost:5173"
	@echo "                  Backend:  uvicorn main:app --reload → http://localhost:8000"
	@echo "  make dev      - Start DB + VectorDB + Backend in Docker (hot-reload)"
	@echo "                  Frontend: npm run dev → http://localhost:5173"
	@echo "                  Backend:  http://localhost:8000"
	@echo "  make prod     - Full production build (all in Docker)"
	@echo "                  Frontend: http://localhost  ← NOT 5173"
	@echo "                  Backend:  http://localhost:8000/docs"
	@echo "  make down     - Stop all containers"
	@echo "  make clean    - Stop all containers AND delete volumes (WARNING: data loss)"
	@echo "  make status   - Show container status"

# Internal task: Ensure .env symlink exists in the deployment folder
init-env:
	@echo "Checking environment configuration..."
	@cd $(COMPOSE_DIR) && [ -L .env ] || ln -s ../.env .env

# Scenario 1: Local Dev (Run uvicorn/npm on host, DB/Weaviate in Docker)
infra: init-env
	cd $(COMPOSE_DIR) && docker compose up db weaviate -d

# Scenario 2: Hybrid Dev (Backend runs in Docker with volume mounting/hot-reload)
dev: init-env
	cd $(COMPOSE_DIR) && docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) up -d

# Scenario 3: Full Production Deployment
prod: init-env
	cd $(COMPOSE_DIR) && docker compose up --build -d
	@echo "✅ Production running:"
	@echo "   Frontend: http://localhost"
	@echo "   Backend:  http://localhost:8000/docs"
		
# Stop services
down:
	cd $(COMPOSE_DIR) && docker compose down

# Wipe everything (containers + volumes)
clean:
	cd $(COMPOSE_DIR) && docker compose down -v

# Show status
status:
	cd $(COMPOSE_DIR) && docker compose ps