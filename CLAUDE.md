# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Bot
```bash
# Run locally with Python
python src/bot.py

# Run with Docker Compose (recommended)
docker compose up -d

# View logs in Docker
docker compose logs -f canillitabot

# Stop the bot
docker compose down

# Restart the Bot
docker compose down && docker compose up -d --build
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

# Test article extraction with preview
./venv/bin/python tools/article_preview.py "https://www.infobae.com/some-article-url"

# Run unit tests
./venv/bin/python -m pytest tests/ -v
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
./venv/bin/python -m pytest tests/test_infobae_integration.py -v

# Test all providers
./venv/bin/python -m pytest tests/test_providers.py -v

# Test extraction for a specific domain with preview
./venv/bin/python tools/article_preview.py "https://www.infobae.com/some-article-url"

# Test extraction for a specific domain programmatically
./venv/bin/python -c "
from src.config import Config
from src.article_extractor import ArticleExtractor
config = Config()
extractor = ArticleExtractor(config)
result = extractor.extract_article('https://www.infobae.com/some-article-url')
print(f'Provider used: {result.get(\"provider\", \"Unknown\")}' if result else 'Failed')
"

# Test Gemini/YouTube functionality
./venv/bin/python -m pytest tests/test_gemini.py -v
./venv/bin/python -m pytest tests/test_youtube.py -v

# Test configuration validation
./venv/bin/python -m pytest tests/test_config.py -v

# Run full integration tests
./venv/bin/python -m pytest tests/test_integration.py -v

# Run all tests
./venv/bin/python -m pytest tests/ -v
```

## Architecture Overview

CanillitaBot is a Python-based Reddit bot that monitors Argentine news subreddits and automatically extracts article content to post as comments, making news more accessible without requiring users to click through links.

### Core Components

**BotManager** (`src/bot.py`): Main orchestrator that coordinates all components in continuous monitoring loops. Handles graceful shutdown, error recovery, and periodic maintenance tasks.

**RedditClient** (`src/reddit_client.py`): Manages all Reddit API interactions through PRAW. Validates submissions, handles comment posting with multi-part splitting for long articles, and implements rate limiting.

**ArticleExtractor** (`src/article_extractor.py`): Multi-strategy content extraction using BeautifulSoup for structured parsing and newspaper3k as fallback. Includes Argentine news site-specific selectors and formatting preservation.

**Database** (`src/database.py`): SQLite-based tracking of processed posts to prevent duplicates. Stores processing statistics, success/failure rates, and article metadata.

**Config** (`src/config.py`): Centralized configuration management loading from YAML files and environment variables. Handles validation of required credentials and settings.

**GeminiClient** (`src/gemini_client.py`): Google Gemini API integration for YouTube video summarization. Handles transcript extraction and AI-powered content analysis.

### Reddit Sub-Components

The Reddit client is composed of specialized components in the `src/reddit/` directory:

**RedditConnection** (`src/reddit/connection.py`): Manages Reddit API authentication and connection handling.

**PostMonitor** (`src/reddit/monitor.py`): Monitors target subreddits for new submissions, validates posts, and detects news articles and YouTube videos.

**CommentManager** (`src/reddit/comments.py`): Handles comment formatting, multi-part comment splitting for long articles, and posting management.

**CommentAnalytics** (`src/reddit/analytics.py`): Provides analytics and monitoring for bot comment performance and engagement.

### Key Architectural Patterns

- **Multi-stage Content Extraction**: Structured BeautifulSoup parsing with newspaper3k fallback ensures maximum extraction success
- **Provider-Based System**: Domain-specific extraction configurations in `config/providers/` for optimized content extraction per news source
- **Intelligent Comment Splitting**: Long articles are automatically split into multiple threaded comments respecting Reddit's character limits
- **Domain-based Article Detection**: Configurable whitelist/blacklist system for determining valid news sources
- **AI Integration**: Google Gemini API for YouTube video transcript analysis and summarization
- **Graceful Error Handling**: Each component handles failures independently without crashing the main loop
- **Rate Limiting**: Built-in delays and Reddit API best practices to avoid being blocked
- **Modular Architecture**: Clear separation of concerns with facade pattern for Reddit operations

### Configuration Files

- `config/settings.yaml`: Main bot configuration (subreddits, intervals, templates, YouTube settings)
- `config/domains.yaml`: News domain whitelist and blocked domains  
- `config/providers/`: Provider-specific extraction configurations
  - `config/providers/infobae.com.yaml`: Infobae-specific selectors and cleanup rules
  - `config/providers/default.yaml`: Fallback configuration for unknown domains
- `.env`: Reddit API credentials and Gemini API key (not committed to repo)

### Data Flow

1. Bot monitors configured subreddits for new posts
2. Posts are validated (age, domain, not already processed)
3. Article content is extracted using provider-based multi-strategy approach
4. YouTube videos are processed through Gemini API for transcript analysis and summarization
5. Content is formatted and split if necessary for Reddit comments
6. Comments are posted as threaded replies with proper attribution
7. Processing results are recorded in SQLite database with success/failure tracking
8. Periodic cleanup removes old database entries and performs maintenance

### Provider-Based News Site Support

The article extractor uses a sophisticated provider-based system for site-specific extraction:
- **Infobae**: Dedicated provider config (`config/providers/infobae.com.yaml`) that removes "Últimas noticias" sections and handles specific content structure
- **Default**: Fallback provider config with generic selectors for Clarín, La Nación, Página/12, TN, Ámbito, etc.
- **Extensible**: Easy to add new providers by creating `config/providers/{domain}.yaml` files
- **Domain-aware**: Automatically detects domain and uses appropriate provider configuration
- **Configurable**: Each provider can specify custom selectors, cleanup patterns, quality thresholds, and extraction methods
- **Quality Assurance**: Text-to-markup ratio validation and content length checks

### AI-Powered Features

- **YouTube Video Processing**: Automatic detection of YouTube links in submissions
- **Transcript Extraction**: Uses youtube-transcript-api to fetch video transcripts
- **Gemini Integration**: Google Gemini API analyzes transcripts and generates contextual summaries
- **Intelligent Summarization**: AI-generated summaries tailored for Reddit comment format
- **Fallback Handling**: Graceful degradation when transcripts are unavailable or API fails

### Error Handling Strategy

Each component implements defensive programming:
- Database errors don't prevent new post processing
- Article extraction failures are logged but don't crash the bot
- Reddit API errors trigger exponential backoff
- Configuration validation prevents startup with invalid settings

This architecture ensures the bot runs reliably 24/7 with minimal intervention while providing comprehensive article extraction for Argentine news sources.