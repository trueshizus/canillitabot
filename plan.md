# Project Cleanup and Refactoring Plan

This plan outlines the steps to improve the project's structure by removing unused files and reorganizing the source code for better clarity and maintainability, following the principles of PEP 20.

## 1. Dead File Removal

The following files have been identified as unused or obsolete and can be safely removed:

-   `src/config_old.py`: This appears to be a backup of a previous configuration system. The project now uses the new dataclass-based `config.py`.
-   `CLAUDE.md`: This file seems to contain notes related to a different AI model and is not relevant to the current project.

## 2. Source Code Reorganization

To make the codebase more intuitive and scalable, the `src/` directory will be restructured to group modules by their primary function.

### Current Structure

```
src/
├── article_extractor.py
├── bot.py
├── config.py
├── dashboard.py
├── database.py
├── gemini_client.py
├── health_server.py
├── monitoring.py
├── queue_manager.py
├── queue_workers.py
├── reddit_client.py
├── utils.py
├── worker.py
├── x_extractor.py
├── providers/
└── reddit/
```

### Proposed New Structure

This structure groups related logic into dedicated packages, making the architecture more explicit and easier to navigate.

```
src/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── bot.py          # Main bot logic (BotManager)
│   ├── config.py       # Configuration loading
│   ├── database.py     # Database management
│   └── monitoring.py   # Monitoring and metrics
├── clients/
│   ├── __init__.py
│   ├── gemini.py       # Renamed from gemini_client.py
│   ├── reddit.py       # Renamed from reddit_client.py
│   └── reddit/         # Sub-package for reddit components
├── extractors/
│   ├── __init__.py
│   ├── article.py      # Renamed from article_extractor.py
│   ├── x.py            # Renamed from x_extractor.py
│   └── providers/      # Provider-specific extraction logic
├── tasks/
│   ├── __init__.py
│   ├── main_worker.py  # Renamed from worker.py
│   └── queue.py        # Renamed from queue_workers.py
├── services/
│   ├── __init__.py
│   ├── dashboard.py    # Flask dashboard
│   └── health.py       # Renamed from health_server.py
└── shared/
    ├── __init__.py
    ├── queue.py        # Renamed from queue_manager.py
    └── utils.py        # Utility functions
```

## 3. Module Refactoring (File Size Guideline)

Several files exceed the recommended 300-line limit, suggesting they could be simplified or split.

-   **`src/config.py` (~550 lines):**
    -   **Suggestion:** Split the dataclass definitions into a separate `src/core/schemas.py` or `src/core/config_models.py` to separate data structure from loading logic.
-   **`src/providers/default.py` (~350 lines):**
    -   **Suggestion:** The `_process_article_structure` and cleanup methods could be moved to a dedicated `src/extractors/formatters.py` module to be reused by other providers.
-   **`src/bot.py` (~400 lines):**
    -   **Suggestion:** The processing logic for different content types (`_process_submission_direct`, `_process_youtube_video`, `_process_x_twitter_post`) could be extracted into a `src/core/processor.py` module, leaving `bot.py` to manage the main loop and orchestration.

This refactoring will result in smaller, more focused modules that are easier to test and maintain.
