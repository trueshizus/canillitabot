# CanillitaBot Tools

Utility scripts for development, testing, and monitoring.

## Available Tools

### `article_preview.py`
Preview how articles will be extracted and formatted as Reddit comments.

```bash
./venv/bin/python tools/article_preview.py "https://example.com/news-article"
./venv/bin/python tools/article_preview.py "https://example.com/news-article" --full
```

### `comment_retriever.py`
Retrieve and analyze CanillitaBot's comment history from Reddit.

```bash
# Get recent comments (readable format)
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

## Usage Notes

- All tools require a working virtual environment with dependencies installed
- Network-dependent tools require proper Reddit API credentials in `.env`
- Use `--help` with any tool to see available options
