# CanillitaBot AI Assistant Context

This document provides essential context for an AI assistant working on the CanillitaBot project. It is based on the principles of context engineering, providing the necessary information to understand the project and assist in its development.

## 1. Project Overview

CanillitaBot is a Python-based Reddit bot that monitors specific subreddits for news articles from Argentine news sources and YouTube videos. When a new article or video is posted, the bot extracts content (or generates AI summaries for videos) and posts it as a comment, making the news more accessible to users without leaving Reddit.

- **Purpose**: To provide accessible news content and video summaries on Reddit.
- **Domain**: Argentine news and YouTube videos.
- **Core Functionality**: Monitor, extract/summarize, and comment.
- **AI Features**: YouTube video summarization using Google Gemini API.

## 2. Core Components

- **`run.py`**: The main entry point of the application. It initializes and starts the `BotManager`.
- **`src/bot.py` (`BotManager`)**: The orchestrator of the bot. It manages the main loop, coordinates the other components, handles graceful shutdown, and integrates AI features.
- **`src/reddit_client.py` (`RedditClient`)**: A facade for all Reddit API interactions, using the PRAW library. It is composed of smaller, more specialized components found in `src/reddit/`.
    - **`src/reddit/connection.py`**: Handles the connection to the Reddit API.
    - **`src/reddit/monitor.py`**: Monitors subreddits for new posts and validates submissions.
    - **`src/reddit/comments.py`**: Manages comment formatting and posting, including splitting long articles into multiple comments.
    - **`src/reddit/analytics.py`**: Provides analytics on bot comments and engagement.
- **`src/article_extractor.py` (`ArticleExtractor`)**: Extracts the content of news articles from their URLs. It uses a provider-based strategy, with specific extractors for different news sites and a fallback to the `newspaper3k` library.
- **`src/gemini_client.py` (`GeminiClient`)**: Handles YouTube video processing using Google Gemini API for transcript analysis and summarization.
- **`src/database.py` (`Database`)**: A SQLite database to keep track of processed posts to avoid duplicates. It also stores metadata, statistics, and processing results.
- **`src/config.py` (`Config`)**: Manages the configuration of the bot, loading settings from YAML files and environment variables.

## 3. Key Architectural Patterns

- **Provider-Based Extraction**: The bot uses a provider pattern to extract content from different news sources. Each provider has its own configuration file in `config/providers/` that specifies how to extract and clean up the content for that specific source. This makes the bot easily extensible to new news sources.
- **AI Integration**: YouTube video processing using Google Gemini API for intelligent summarization of video content through transcript analysis.
- **Facade Pattern**: The `RedditClient` acts as a facade, providing a simple interface to the more complex underlying components that handle different aspects of the Reddit interaction.
- **Dependency Injection**: The `BotManager` creates instances of the `Config`, `RedditClient`, `ArticleExtractor`, `GeminiClient`, and `Database` classes and uses them throughout its lifecycle. This makes the components loosely coupled and easier to test.
- **Defensive Programming**: The bot is designed to be resilient. Errors in processing a single submission or subreddit do not crash the entire bot.

## 4. Configuration

- **`config/settings.yaml`**: The main configuration file for the bot. It defines the subreddits to monitor, the comment templates, YouTube settings, and other operational parameters.
- **`config/domains.yaml`**: Contains whitelists and blacklists of domains to determine which URLs should be processed.
- **`config/providers/*.yaml`**: Provider-specific configurations for article extraction (e.g., `infobae.com.yaml`, `default.yaml`).
- **`.env`**: Contains the Reddit API credentials and Gemini API key. This file is not committed to the repository.

## 5. Development Commands

- **Running the bot**: `python run.py` or `docker compose up -d`
- **Running tests**: `./venv/bin/python -m pytest tests/ -v`
- **Previewing article extraction**: `./venv/bin/python tools/article_preview.py "<URL>"`
- **Retrieving comment data**: `./venv/bin/python tools/comment_retriever.py <command> [options]`
- **Testing specific components**: `./venv/bin/python -m pytest tests/test_<component>.py -v`

By understanding this context, an AI assistant can provide more relevant and accurate assistance in developing and maintaining CanillitaBot.
