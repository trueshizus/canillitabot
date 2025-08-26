# CanillitaBot Makefile
# Provides standard commands for development and deployment workflow

.PHONY: help start stop restart test build deploy clean logs status health setup

# Default target
help:
	@echo "CanillitaBot Development Commands:"
	@echo ""
	@echo "Development:"
	@echo "  make setup     - Set up development environment"
	@echo "  make start     - Start the bot locally or with Docker Compose"
	@echo "  make stop      - Stop the bot"
	@echo "  make restart   - Restart the bot"
	@echo "  make logs      - View bot logs"
	@echo "  make status    - Check bot status"
	@echo ""
	@echo "Testing:"
	@echo "  make test      - Run all tests"
	@echo "  make test-unit - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make lint      - Run code linting"
	@echo ""
	@echo "Building:"
	@echo "  make build     - Build Docker image"
	@echo "  make build-prod - Build optimized production image"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy    - Deploy to production (Digital Ocean)"
	@echo "  make deploy-staging - Deploy to staging environment"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean     - Clean up Docker images and containers"
	@echo "  make health    - Check bot health and database stats"
	@echo "  make backup    - Backup database"
	@echo ""

# Development Environment Setup
setup:
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file from template - please configure it"; \
	fi
	@echo "Testing configuration..."
	@./venv/bin/python -c "from src.config import Config; c = Config(); c.validate(); print('✓ Configuration valid')"
	@echo "Testing article extraction..."
	@./venv/bin/python -c "from src.article_extractor import ArticleExtractor; from src.config import Config; ae = ArticleExtractor(Config()); print('✓ Article extractor ready')"
	@echo "Setup complete!"

# Start commands
start:
	@if [ "$(MODE)" = "local" ]; then \
		echo "Starting bot locally..."; \
		./venv/bin/python src/bot.py; \
	else \
		echo "Starting bot with Docker Compose..."; \
		docker compose up -d; \
		echo "Bot started. Use 'make logs' to view output."; \
	fi

start-local:
	@echo "Starting bot locally..."
	@./venv/bin/python src/bot.py

start-docker:
	@echo "Starting bot with Docker Compose..."
	@docker compose up -d
	@echo "Bot started. Use 'make logs' to view output."

# Stop and restart
stop:
	@echo "Stopping bot..."
	@docker compose down
	@echo "Bot stopped."

restart:
	@echo "Restarting bot..."
	@docker compose down && docker compose up -d --build
	@echo "Bot restarted."

# Logs and status
logs:
	@docker compose logs -f canillitabot

status:
	@echo "Docker container status:"
	@docker compose ps
	@echo ""
	@echo "Recent processing activity:"
	@./venv/bin/python -c "from src.database import Database; from src.config import Config; db = Database(Config()); print(db.get_processing_stats())"

health:
	@echo "Checking bot health..."
	@echo ""
	@echo "Configuration validation:"
	@./venv/bin/python -c "from src.config import Config; c = Config(); c.validate(); print('✓ Configuration valid')"
	@echo ""
	@echo "Database connection:"
	@./venv/bin/python -c "from src.database import Database; from src.config import Config; db = Database(Config()); print('✓ Database accessible')"
	@echo ""
	@echo "Reddit connection:"
	@./venv/bin/python -c "from src.reddit_client import RedditClient; from src.config import Config; rc = RedditClient(Config()); print('✓ Reddit connected')"
	@echo ""
	@echo "Processing statistics (last 24h):"
	@./venv/bin/python -c "from src.database import Database; from src.config import Config; db = Database(Config()); stats = db.get_processing_stats(days=1); print(f'Processed: {stats.get(\"total_processed\", 0)}, Success Rate: {stats.get(\"success_rate\", 0):.1%}' if stats else 'No recent activity')"

# Testing
test:
	@echo "Running all tests..."
	@./venv/bin/python -m pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	@./venv/bin/python -m pytest tests/test_config.py tests/test_providers.py -v

test-integration:
	@echo "Running integration tests..."
	@./venv/bin/python -m pytest tests/test_integration.py tests/test_infobae_integration.py tests/test_gemini.py tests/test_youtube.py -v

lint:
	@echo "Running code linting..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 src/ --max-line-length=120 --ignore=E203,W503; \
	else \
		echo "flake8 not installed, skipping lint check"; \
	fi

# Building
build:
	@echo "Building Docker image..."
	@docker build -t canillitabot:latest .
	@echo "Build complete: canillitabot:latest"

build-prod:
	@echo "Building optimized production image..."
	@docker build -t canillitabot:prod --target production .
	@echo "Production build complete: canillitabot:prod"

# Deployment
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
	@echo "Deployment to $(SERVER) complete!"

deploy-staging:
	@echo "Deploying to staging environment..."
	@docker compose -f docker-compose.staging.yml up -d --build

# Maintenance
clean:
	@echo "Cleaning up Docker resources..."
	@docker system prune -f
	@docker volume prune -f
	@echo "Cleanup complete."

backup:
	@echo "Creating database backup..."
	@mkdir -p backups
	@cp data/processed_posts.db backups/processed_posts_$(shell date +%Y%m%d_%H%M%S).db
	@echo "Database backed up to backups/ directory."

# Development utilities
preview-article:
	@if [ -z "$(URL)" ]; then \
		echo "Usage: make preview-article URL='https://example.com/article'"; \
	else \
		./venv/bin/python tools/article_preview.py "$(URL)"; \
	fi

comment-stats:
	@echo "Recent bot comment activity:"
	@./venv/bin/python tools/comment_retriever.py stats

get-comments:
	@echo "Recent bot comments:"
	@./venv/bin/python tools/comment_retriever.py comments --limit 10

# Queue management
queue-status:
	@echo "Queue system status:"
	@./venv/bin/python -c "from src.queue_manager import QueueManager; from src.config import Config; qm = QueueManager(Config()); print(qm.get_queue_stats())"

queue-clear:
	@echo "Clearing all queues..."
	@./venv/bin/python -c "from src.queue_manager import QueueManager; from src.config import Config; qm = QueueManager(Config()); qm.clear_all_queues(); print('All queues cleared')"

queue-failed:
	@echo "Failed jobs:"
	@./venv/bin/python -c "from src.queue_manager import QueueManager; from src.config import Config; qm = QueueManager(Config()); import json; print(json.dumps(qm.get_failed_jobs(), indent=2))"

start-worker:
	@echo "Starting queue worker..."
	@./venv/bin/python src/worker.py

start-dashboard:
	@echo "Starting web dashboard..."
	@./venv/bin/python src/dashboard.py

dashboard-url:
	@echo "Dashboard URL: http://localhost:5000"