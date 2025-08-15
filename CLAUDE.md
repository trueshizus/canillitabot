# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Bot
```bash
# Run locally with Python
python src/bot.py

# Run with Docker Compose (recommended)
docker-compose up -d

# View logs in Docker
docker-compose logs -f canillitabot

# Stop the bot
docker-compose down
```

### Development Setup
```bash
# IMPORTANT: Always use the virtual environment for this project
# The venv is already set up and contains all dependencies

# Copy environment template (if not exists)
cp .env.example .env
# Then edit .env with your Reddit API credentials

# Test configuration using venv
./venv/bin/python -c "from src.config import Config; c = Config(); c.validate(); print('✓ Configuration valid')"

# Test article extraction using venv
./venv/bin/python -c "from src.article_extractor import ArticleExtractor; from src.config import Config; ae = ArticleExtractor(Config()); print('✓ Article extractor ready')"

# If you need to install additional dependencies
./venv/bin/python -m pip install package_name
```

### Testing and Validation
```bash
# Test Reddit connection (using venv)
./venv/bin/python -c "from src.reddit_client import RedditClient; from src.config import Config; rc = RedditClient(Config()); print('✓ Reddit connected')"

# Test database (using venv)
./venv/bin/python -c "from src.database import Database; from src.config import Config; db = Database(Config()); print('✓ Database initialized')"

# Check processing stats (using venv)
./venv/bin/python -c "from src.database import Database; from src.config import Config; db = Database(Config()); print(db.get_processing_stats())"
```

### Comment Analysis and Monitoring
```bash
# Get recent CanillitaBot comments (readable format) - using venv
./venv/bin/python tools/comment_retriever.py comments

# Get comment summary
./venv/bin/python tools/comment_retriever.py comments --format summary

# Get comments from specific subreddit
./venv/bin/python tools/comment_retriever.py comments --subreddit argentina

# Get comment statistics
./venv/bin/python tools/comment_retriever.py stats

# Get replies to a specific comment
./venv/bin/python tools/comment_retriever.py replies --comment-id COMMENT_ID

# Get JSON output for programmatic use
./venv/bin/python tools/comment_retriever.py comments --format json --limit 50
```

### Provider-Based Article Extraction Testing
```bash
# Test the new provider-based extraction system (removes "Últimas noticias" sections)
./venv/bin/python tests/test_infobae_provider.py

# Test extraction for a specific domain
./venv/bin/python -c "
from src.config import Config
from src.article_extractor import ArticleExtractor
config = Config()
extractor = ArticleExtractor(config)
result = extractor.extract_article('https://www.infobae.com/some-article-url')
print(f'Provider used: {result.get(\"provider\", \"Unknown\")}' if result else 'Failed')
"
```

## Architecture Overview

CanillitaBot is a Python-based Reddit bot that monitors Argentine news subreddits and automatically extracts article content to post as comments, making news more accessible without requiring users to click through links.

### Core Components

**BotManager** (`src/bot.py`): Main orchestrator that coordinates all components in continuous monitoring loops. Handles graceful shutdown, error recovery, and periodic maintenance tasks.

**RedditClient** (`src/reddit_client.py`): Manages all Reddit API interactions through PRAW. Validates submissions, handles comment posting with multi-part splitting for long articles, and implements rate limiting.

**ArticleExtractor** (`src/article_extractor.py`): Multi-strategy content extraction using BeautifulSoup for structured parsing and newspaper3k as fallback. Includes Argentine news site-specific selectors and formatting preservation.

**Database** (`src/database.py`): SQLite-based tracking of processed posts to prevent duplicates. Stores processing statistics, success/failure rates, and article metadata.

**Config** (`src/config.py`): Centralized configuration management loading from YAML files and environment variables. Handles validation of required credentials and settings.

### Key Architectural Patterns

- **Multi-stage Content Extraction**: Structured BeautifulSoup parsing with newspaper3k fallback ensures maximum extraction success
- **Intelligent Comment Splitting**: Long articles are automatically split into multiple threaded comments respecting Reddit's character limits
- **Domain-based Article Detection**: Configurable whitelist/blacklist system for determining valid news sources
- **Graceful Error Handling**: Each component handles failures independently without crashing the main loop
- **Rate Limiting**: Built-in delays and Reddit API best practices to avoid being blocked

### Configuration Files

- `config/settings.yaml`: Main bot configuration (subreddits, intervals, templates)
- `config/domains.yaml`: News domain whitelist and blocked domains  
- `config/providers/`: Provider-specific extraction configurations
  - `config/providers/infobae.yaml`: Infobae-specific selectors and cleanup rules
  - `config/providers/default.yaml`: Fallback configuration for unknown domains
- `.env`: Reddit API credentials (not committed to repo)

### Data Flow

1. Bot monitors configured subreddits for new posts
2. Posts are validated (age, domain, not already processed)
3. Article content is extracted using multi-strategy approach
4. Content is formatted and split if necessary for Reddit comments
5. Comments are posted as threaded replies
6. Processing results are recorded in SQLite database
7. Periodic cleanup removes old database entries

### Provider-Based News Site Support

The article extractor uses a provider-based system for site-specific extraction:
- **Infobae**: Dedicated provider config (`config/providers/infobae.yaml`) that removes "Últimas noticias" sections
- **Default**: Fallback provider config with generic selectors for Clarín, La Nación, Página/12, TN, Ámbito, etc.
- **Extensible**: Easy to add new providers by creating `config/providers/{domain}.yaml` files
- **Domain-aware**: Automatically detects domain and uses appropriate provider configuration
- **Configurable**: Each provider can specify custom selectors, cleanup patterns, and quality thresholds

### Error Handling Strategy

Each component implements defensive programming:
- Database errors don't prevent new post processing
- Article extraction failures are logged but don't crash the bot
- Reddit API errors trigger exponential backoff
- Configuration validation prevents startup with invalid settings

This architecture ensures the bot runs reliably 24/7 with minimal intervention while providing comprehensive article extraction for Argentine news sources.