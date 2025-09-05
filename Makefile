# CanillitaBot Makefile

# Default SSH host alias for production deploys (configurable)
HOST ?= bot
# Remote directory where the repo lives (relative to remote user's $HOME or absolute)
REMOTE_DIR ?= canillitabot
# Git branch to deploy
BRANCH ?= main

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
	@echo "Deploying to production host: $(HOST) in '$(REMOTE_DIR)' on branch '$(BRANCH)'"
	@ssh $(HOST) 'set -euo pipefail; \
		cd $(REMOTE_DIR) && \
		git fetch --all --prune && \
		( git rev-parse --verify $(BRANCH) >/dev/null 2>&1 && git checkout $(BRANCH) || true ) && \
		git pull --rebase --autostash origin $(BRANCH) && \
		docker compose build && \
		docker compose up -d && \
		docker compose ps'

health:
	@echo "Checking bot health..."
	@./venv/bin/python -c "from src.core.config import Config; c = Config(); c.validate(); print('✓ Configuration valid')"
	@./venv/bin/python -c "from src.core.database import Database; from src.core.config import Config; db = Database(Config()); print('✓ Database accessible')"
	@echo "Health check complete."

test:
	@echo "Running tests..."
	@docker compose run --rm test
