# TODO: Refactor bot.py

This file has grown too large and is responsible for too many things. The following is a plan to split it into smaller, more manageable modules.

-   **[ ] Create `src/core/lifecycle.py`:**
    -   Move the bot's startup, shutdown, and main loop logic into a `BotLifecycle` class.
    -   This includes the `start`, `stop`, `shutdown_gracefully`, `_interruptible_sleep`, and `_cleanup` methods.
    -   The `BotManager` will instantiate and run the `BotLifecycle`.

-   **[ ] Create `src/core/cycle.py`:**
    -   Move the processing cycle logic into a `ProcessingCycle` class.
    -   This includes the `_process_cycle`, `_process_subreddit`, and `_periodic_cleanup` methods.
    -   The `BotLifecycle` will call the `ProcessingCycle` in its main loop.

-   **[ ] Create `src/core/submission.py`:**
    -   Move the submission handling logic into a `SubmissionHandler` class.
    -   This includes the `_process_submission`, `_enqueue_submission`, and `_determine_content_type` methods.
    -   The `ProcessingCycle` will use the `SubmissionHandler` to process each post.

-   **[ ] Update `src/core/bot.py`:**
    -   The `BotManager` class will be simplified to be the main entry point and orchestrator.
    -   It will initialize all the components (clients, extractors, database, etc.) and then pass them to the new `BotLifecycle`, `ProcessingCycle`, and `SubmissionHandler` classes.
    -   The `__init__` method will be significantly smaller.

-   **[ ] Review and update imports:**
    -   After the refactoring, review all the new files and update the import statements to reflect the new structure.
