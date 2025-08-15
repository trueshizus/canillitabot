# CanillitaBot - Reddit News Bot

A Reddit bot that automatically extracts and posts article content as comments when news articles are submitted to monitored subreddits.

- Monitor specified subreddit(s) for new posts containing news article links
- Extract full article content from linked to news sources
- Post the extracted content as a comment to make articles accessible without clicking through
- Handle various news domains and formats reliably
- Run continuously with minimal maintenance required

## Getting Started

1. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

## How It Works

1. **Post Monitoring**: Uses Reddit API to monitor new submissions in target subreddit(s)
2. **Article Detection**: Identifies posts containing links to news websites using domain filtering
3. **Content Extraction**: Fetches and parses article content using web scraping/NLP techniques
4. **Comment Creation**: Posts extracted content as a formatted comment on the original submission
5. **Rate Limiting**: Respects Reddit API limits and implements backoff strategies

## Architecture & Tools

### Reddit Integration Options
- **PRAW (Python Reddit API Wrapper)**: Most mature and feature-complete option
  - Handles authentication, rate limiting, and streaming
  - Active community and extensive documentation
  - Built-in support for comment posting and submission monitoring

### Article Content Extraction
- **newspaper3k**: Python library for article extraction
  - Handles multiple news formats and domains
  - Built-in NLP for content cleaning
  - Fallback to BeautifulSoup for complex sites
- **Readability**: Alternative parsing option for better content quality

### Technology Stack
- **Language**: Python 3.9+
- **Reddit API**: PRAW
- **Web Scraping**: newspaper3k + requests + BeautifulSoup4
- **Database**: SQLite (for tracking processed posts)
- **Logging**: Python logging module
- **Configuration**: Environment variables + YAML config

### Deployment Options

#### Option 1: Cloud VPS (Recommended)
- **Platform**: DigitalOcean Droplet, AWS EC2, or similar
- **Process Management**: systemd service
- **Monitoring**: Basic health checks and log rotation
- **Cost**: $5-10/month for basic VPS

#### Option 2: Serverless
- **Platform**: AWS Lambda + EventBridge
- **Trigger**: Scheduled execution (every 1-5 minutes)
- **Storage**: DynamoDB for state management
- **Cost**: Near-free for moderate usage

#### Option 3: Container Platform
- **Platform**: Railway, Render, or Heroku
- **Deployment**: Docker container with scheduler
- **Database**: Managed PostgreSQL
- **Cost**: $5-15/month

## Project Structure
```
canillita-bot/
├── src/
│   ├── bot.py              # Main bot logic
│   ├── reddit_client.py    # Reddit API interactions
│   ├── article_extractor.py # News content extraction
│   ├── database.py         # Data persistence
│   └── config.py          # Configuration management
├── config/
│   ├── settings.yaml      # Bot configuration
│   └── domains.yaml       # Supported news domains
├── tests/
├── requirements.txt
├── Dockerfile
└── README.md
```

## Key Features

### Smart Article Detection
- Configurable domain whitelist for news sources
- URL pattern matching for article identification
- Duplicate post prevention

### Content Processing
- Article text extraction and cleaning
- Automatic summarization for long articles
- Preservation of key formatting (headlines, lists)
- Source attribution and original link reference

### Reddit Integration
- Respectful rate limiting (1 request per 2 seconds minimum)
- Error handling for deleted posts, private subreddits
- Comment formatting with proper markdown
- Moderation-friendly operation

### Reliability Features
- Persistent storage of processed posts
- Graceful error handling and recovery
- Configurable retry logic
- Health monitoring and logging

## Configuration

### Environment Variables
- `REDDIT_CLIENT_ID`: Reddit app client ID
- `REDDIT_CLIENT_SECRET`: Reddit app client secret
- `REDDIT_USERNAME`: Bot account username
- `REDDIT_PASSWORD`: Bot account password
- `REDDIT_USER_AGENT`: Descriptive user agent string

### Settings
- Target subreddit(s)
- Supported news domains
- Comment template/formatting
- Processing intervals
- Rate limiting parameters

## Considerations

- Respects robots.txt and website rate limits
- Provides proper attribution to original sources
- Operates transparently with clear bot identification
- Follows Reddit's API Terms of Service
- Does not post duplicate content or spam

## Next Steps

1. Set up Reddit API credentials and create bot account
2. Implement core bot functionality with PRAW
3. Integrate article extraction with newspaper3k
4. Add database layer for tracking processed posts
5. Create configuration system and error handling
6. Test with a small subreddit before scaling
7. Deploy to chosen hosting platform
8. Monitor and optimize performance

## Legal & Compliance

- Ensure compliance with news website terms of service
- Respect copyright laws (fair use for excerpts)
- Follow Reddit community guidelines
- Implement proper content attribution