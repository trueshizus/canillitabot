# CanillitaBot Development Tools

Utility scripts for development, testing, and monitoring of the CanillitaBot Reddit news bot.

## Available Tools

### `article_preview.py`
Preview how articles will be extracted and formatted as Reddit comments. Tests the provider-based extraction system.

```bash
# Preview article extraction
./venv/bin/python tools/article_preview.py "https://www.infobae.com/news-article"

# Show full extraction details
./venv/bin/python tools/article_preview.py "https://www.clarin.com/news-article" --full

# Test with different providers
./venv/bin/python tools/article_preview.py "https://www.lanacion.com.ar/news-article"
```

**Features:**
- Tests provider-specific extraction rules
- Shows formatted comment preview
- Displays extraction metadata and provider used
- Validates content quality and cleanup

### `comment_retriever.py`
Retrieve and analyze CanillitaBot's comment history from Reddit. Monitor bot performance and engagement.

```bash
# Get recent comments (readable format)
./venv/bin/python tools/comment_retriever.py comments

# Get comment summary with statistics
./venv/bin/python tools/comment_retriever.py comments --format summary

# Get comments from specific subreddit
./venv/bin/python tools/comment_retriever.py comments --subreddit argentina_dev

# Get detailed comment statistics
./venv/bin/python tools/comment_retriever.py stats

# Get replies to a specific comment
./venv/bin/python tools/comment_retriever.py replies --comment-id COMMENT_ID

# Get JSON output for programmatic use
./venv/bin/python tools/comment_retriever.py comments --format json --limit 50

# Monitor recent activity
./venv/bin/python tools/comment_retriever.py comments --limit 10 --format summary
```

**Features:**
- Real-time comment monitoring
- Engagement analytics (upvotes, replies, awards)
- Subreddit-specific filtering
- Multiple output formats (text, summary, JSON)
- Reply thread analysis

## Testing Integration

These tools integrate with the test suite for comprehensive validation:

```bash
# Test article extraction with multiple sources
./venv/bin/python -c "
import sys; sys.path.insert(0, 'tools')
from article_preview import test_multiple_sources
test_multiple_sources(['infobae.com', 'clarin.com', 'lanacion.com.ar'])
"

# Monitor bot performance after deployment
./venv/bin/python tools/comment_retriever.py stats --days 7
```

## Usage Notes

- **Virtual Environment**: All tools require the included virtual environment (`./venv/bin/python`)
- **API Credentials**: Network-dependent tools require proper Reddit API credentials in `.env`
- **Provider Testing**: Use `article_preview.py` to test new provider configurations
- **Performance Monitoring**: Use `comment_retriever.py` for ongoing bot health monitoring
- **Help**: Use `--help` with any tool to see all available options

## Development Workflow

1. **Test Article Extraction**: Use `article_preview.py` to verify extraction quality
2. **Deploy Changes**: Update bot and restart with `docker compose`
3. **Monitor Performance**: Use `comment_retriever.py` to track success rates
4. **Iterate**: Adjust provider configs based on performance data
