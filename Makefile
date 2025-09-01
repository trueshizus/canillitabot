# CanillitaBot Makefile

.PHONY: help up stop build deploy health

help:
	@echo "CanillitaBot Commands:"
	@echo "  make up      - Start containers"
	@echo "  make stop    - Stop containers"
	@echo "  make build   - Build images"
	@echo "  make deploy  - Deploy to production"
	@echo "  make health  - Check bot health"

up:
	@docker compose up -d

stop:
	@docker compose down

build:
	@docker compose build

deploy:
	@echo "Deploying to production..."
	@if [ -z "$(SERVER)" ]; then \
		echo "Error: SERVER variable not set. Usage: make deploy SERVER=your-droplet-ip"; \
		exit 1; \
	fi
	@echo "Building and pushing to $(SERVER)..."
	@docker save canillitabot:latest | ssh root@$(SERVER) 'docker load'
	@scp docker-compose.yml root@$(SERVER):/opt/canillitabot/
	@scp .env root@$(SERVER):/opt/canillitabot/
	@ssh root@$(SERVER) 'cd /opt/canillitabot && docker compose down && docker compose up -d'
	@echo "Deployment complete!"

health:
	@echo "Checking bot health..."
	@./venv/bin/python -c "from src.core.config import Config; c = Config(); c.validate(); print('✓ Configuration valid')"
	@./venv/bin/python -c "from src.core.database import Database; from src.core.config import Config; db = Database(Config()); print('✓ Database accessible')"
	@echo "Health check complete."
