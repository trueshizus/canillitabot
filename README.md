# CanillitaBot

A Reddit bot that posts news articles as comments.

## Quick Start

1.  **Configure:** Copy `.env.example` to `.env` and fill in your Reddit API credentials.
2.  **Build:** `make build`
3.  **Run:** `make start`

## Development Tools

A set of utility scripts are available in the `tools/` directory to assist with development and monitoring.

### `article_preview.py`

Preview how an article will be extracted and formatted.

```bash
./venv/bin/python tools/article_preview.py "<article_url>"
```

### `comment_retriever.py`

Retrieve and analyze the bot's comment history.

```bash
# Get the 10 most recent comments
./venv/bin/python tools/comment_retriever.py comments --limit 10
```

### `enqueue_post.py`

Manually enqueue a Reddit post for processing.

```bash
./venv/bin/python tools/enqueue_post.py "<reddit_post_url>"
```