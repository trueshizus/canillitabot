# CanillitaBot - Reddit Argentina News Bot

A sophisticated Reddit bot that automatically extracts and posts article content as comments when news articles are submitted to monitored subreddits. Designed specifically for Argentine news sources with advanced content extraction and AI-powered video summarization.

## ✨ Key Features

- 🔍 **Smart Content Detection**: Monitor subreddits for news articles and YouTube videos
- 📰 **Advanced Article Extraction**: Provider-based system with site-specific optimizations
- 🎥 **YouTube Video Summarization**: AI-powered summaries using Google Gemini API
- 🧠 **Intelligent Content Cleanup**: Removes ads, "latest news" sections, and clutter
- 💬 **Multi-part Comment Threading**: Automatically splits long articles across threaded comments
- 🗄️ **Duplicate Prevention**: SQLite database tracks processed posts
- 🔄 **Robust Error Handling**: Graceful recovery with exponential backoff
- 🏗️ **Production Ready**: Docker deployment with health checks

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Reddit API credentials (see [Reddit App creation guide](https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps))
- Google Gemini API key (optional, for YouTube video summarization)

### Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/trueshizus/botonar.git
   cd canillitabot
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Reddit API credentials and Gemini API key
   ```

3. **Run with Docker Compose (Recommended)**
   ```bash
   docker compose up -d
   ```

4. **Monitor logs**
   ```bash
   docker compose logs -f canillitabot
   ```

### Alternative: Local Development
```bash
# Use the included virtual environment
./venv/bin/python run.py

# Or run tests
./venv/bin/python -m pytest tests/ -v
```

## How It Works

1. **Post Monitoring**: Uses Reddit API to monitor new submissions in target subreddit(s)
2. **Article Detection**: Identifies posts containing links to news websites using domain filtering
3. **Content Extraction**: Fetches and parses article content using web scraping/NLP techniques
4. **Comment Creation**: Posts extracted content as a formatted comment on the original submission
5. **Rate Limiting**: Respects Reddit API limits and implements backoff strategies

## 🏗️ Architecture Overview

### Core Components

- **BotManager** (`src/bot.py`): Main orchestrator with continuous monitoring loops, graceful shutdown, and error recovery
- **RedditClient** (`src/reddit_client.py`): Facade for Reddit API interactions via PRAW with specialized sub-components:
  - **Connection** (`src/reddit/connection.py`): Handles Reddit API authentication and connection
  - **PostMonitor** (`src/reddit/monitor.py`): Monitors subreddits for new submissions
  - **CommentManager** (`src/reddit/comments.py`): Manages comment formatting and multi-part posting
  - **CommentAnalytics** (`src/reddit/analytics.py`): Provides comment performance analytics
- **ArticleExtractor** (`src/article_extractor.py`): Provider-based content extraction with site-specific optimizations
- **GeminiClient** (`src/gemini_client.py`): AI-powered YouTube video summarization
- **Database** (`src/database.py`): SQLite-based post tracking with automatic cleanup
- **Config** (`src/config.py`): Centralized configuration management from YAML and environment variables

### Technology Stack
- **Language**: Python 3.11+
- **Reddit API**: PRAW (Python Reddit API Wrapper)
- **AI Integration**: Google Gemini API for video summarization
- **Web Scraping**: newspaper3k + BeautifulSoup4 with provider-specific selectors
- **Database**: SQLite with automatic cleanup and vacuum
- **Deployment**: Docker with health checks and persistent volumes
- **Configuration**: YAML files + environment variables
- **Testing**: pytest with comprehensive test suite

## 🧪 Development & Testing

### Available Tools
```bash
# Test article extraction
./venv/bin/python tools/article_preview.py "https://www.infobae.com/some-article"

# Analyze bot comments
./venv/bin/python tools/comment_retriever.py comments --format summary

# Run test suite
./venv/bin/python -m pytest tests/ -v

# Test configuration
./venv/bin/python -c "from src.config import Config; Config().validate(); print('✓ Config valid')"
```

### Docker Commands
```bash
# Start bot
docker compose up -d

# View logs
docker compose logs -f canillitabot

# Restart with rebuild
docker compose down && docker compose up -d --build

# Stop bot
docker compose down
```

## 📊 Monitoring & Analytics

The bot includes comprehensive monitoring capabilities:
- **Processing Statistics**: Success rates, failure analysis, performance metrics
- **Comment Analytics**: Upvote tracking, reply monitoring, engagement analysis
- **Database Health**: Automatic cleanup, vacuum operations, size monitoring
- **Error Tracking**: Detailed logging with structured error information

Access statistics via the comment retriever tool or database queries.

## 📁 Project Structure
```
canillitabot/
├── src/                    # Source code
│   ├── bot.py             # Main bot orchestrator (BotManager)
│   ├── reddit_client.py   # Reddit API facade
│   ├── article_extractor.py # Content extraction engine
│   ├── gemini_client.py   # AI video summarization
│   ├── database.py        # SQLite data management
│   ├── config.py          # Configuration management
│   ├── utils.py           # Utility functions
│   ├── providers/         # Article extraction providers
│   │   ├── base.py        # Provider base classes
│   │   ├── default.py     # Default fallback provider
│   │   └── infobae.py     # Infobae-specific provider
│   └── reddit/            # Reddit API components
│       ├── connection.py  # API connection management
│       ├── monitor.py     # Post monitoring
│       ├── comments.py    # Comment management
│       └── analytics.py   # Comment analytics
├── config/                # Configuration files
│   ├── settings.yaml      # Main bot settings
│   ├── domains.yaml       # Supported news domains
│   └── providers/         # Provider-specific configs
│       ├── default.yaml   # Generic extraction rules
│       └── infobae.com.yaml # Infobae-specific rules
├── tests/                 # Test suite
│   ├── test_e2e.py        # End-to-end tests
│   ├── test_providers.py  # Provider tests
│   ├── test_config.py     # Configuration tests
│   ├── test_gemini.py     # AI integration tests
│   ├── test_integration.py # Integration tests
│   └── test_youtube.py    # YouTube processing tests
├── tools/                 # Development utilities
│   ├── article_preview.py # Test article extraction
│   └── comment_retriever.py # Analyze bot comments
├── data/                  # Application data
│   └── processed_posts.db # SQLite database
├── logs/                  # Application logs
├── docker-compose.yml     # Docker orchestration
├── Dockerfile            # Container definition
├── requirements.txt      # Python dependencies
└── run.py               # Application entry point
```

## 🎯 Advanced Features

### Provider-Based Article Extraction
- **Site-Specific Optimization**: Dedicated extractors for major Argentine news outlets
- **Intelligent Content Cleanup**: Removes "Últimas noticias" sections, ads, and social media clutter
- **Fallback Strategy**: Multi-layer extraction using BeautifulSoup → newspaper3k → manual parsing
- **Quality Validation**: Text-to-markup ratio checks and content length validation
- **Extensible Design**: Easy to add new providers via YAML configuration

### AI-Powered Video Summarization
- **YouTube Integration**: Automatic detection and processing of YouTube video links
- **Transcript Analysis**: Uses Google Gemini API to analyze video transcripts
- **Smart Summarization**: Contextual summaries tailored for Argentine audiences
- **Fallback Handling**: Graceful degradation when transcripts unavailable

### Intelligent Comment Management
- **Multi-Part Threading**: Long articles automatically split across threaded comments
- **Template System**: Customizable comment templates with proper attribution
- **Rate Limiting**: Respectful Reddit API usage with exponential backoff
- **Error Recovery**: Robust handling of deleted posts, private subreddits, and API errors

### Production-Grade Reliability
- **Docker Deployment**: Container-based deployment with health checks
- **Database Management**: Automatic cleanup of old entries with periodic vacuum
- **Comprehensive Logging**: Structured logging with rotation and monitoring
- **Graceful Shutdown**: Signal handling for clean container stops
- **Statistics Tracking**: Processing success rates and performance metrics

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# Reddit API (Required)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_bot_username
REDDIT_PASSWORD=your_bot_password
REDDIT_USER_AGENT=CanillitaBot/1.0 by YourUsername

# Google Gemini API (Optional - for YouTube videos)
GEMINI_API_KEY=your_gemini_api_key

# Subreddit Override (Optional)
REDDIT_SUBREDDITS=argentina,argentina_dev,news
```

### Main Settings (config/settings.yaml)
- **Target Subreddits**: Currently monitoring `r/argentina_dev`
- **Check Interval**: 30 seconds between monitoring cycles
- **YouTube Support**: Enabled with AI summarization
- **Comment Templates**: Customizable with proper attribution
- **Processing Limits**: 10,000 char comments, 50,000 char articles
- **Database Cleanup**: 30-day retention policy

### Supported News Domains (config/domains.yaml)
- **Major Outlets**: Clarín, La Nación, Página/12, Infobae, TN, C5N
- **Regional Sources**: Los Andes, La Voz, El Doce, Río Negro
- **Business Media**: Cronista, iProfesional, Ámbito
- **Blocked Domains**: Social media and non-news sites

## 🤝 Contributing

### Adding New News Sources
1. Create provider config: `config/providers/newdomain.com.yaml`
2. Define extraction selectors and cleanup rules
3. Add domain to `config/domains.yaml`
4. Test with `tools/article_preview.py`

### Development Workflow
1. Use the included virtual environment: `./venv/bin/python`
2. Run tests before committing: `pytest tests/ -v`
3. Test extraction thoroughly with preview tool
4. Follow existing code patterns and documentation

## 📄 License & Compliance

- **License**: See LICENSE file
- **Reddit Compliance**: Follows Reddit API Terms of Service and bot guidelines
- **Content Attribution**: Proper source attribution with original links
- **Rate Limiting**: Respectful API usage with built-in delays
- **Copyright**: Fair use excerpts with full attribution

## 🔗 Links

- **Repository**: [trueshizus/botonar](https://github.com/trueshizus/botonar)
- **Reddit API**: [PRAW Documentation](https://praw.readthedocs.io/)
- **Google Gemini**: [Gemini API Documentation](https://cloud.google.com/gemini)

---

*CanillitaBot v1.0 - Making Argentine news more accessible on Reddit* 🇦🇷