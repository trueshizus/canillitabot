# Test Plan: Live End-to-End (E2E) Suite

This document outlines the plan to create a new suite of end-to-end tests that validate the bot's functionality in a live environment. The tests will interact with a locally running instance of the CanillitaBot and verify its responses to specific Reddit posts.

### Section 1: Guiding Principles

-   **Live Interaction:** Tests will run against a live Reddit subreddit (`/r/argentina_dev`) to ensure the bot works with the current Reddit API and website structures.
-   **Local Bot Instance:** The tests will trigger a locally running instance of the bot, started via `docker-compose up`.
-   **Prerequisite-Based:** Each test case will rely on a pre-existing Reddit post that acts as the test's trigger.
-   **Validation:** The core of each test is to fetch the comment posted by the bot and assert that its content is correct and well-formatted for the given link type.

---

### Section 2: Initial Setup & Prerequisites

Before the tests can be run, a one-time setup is required to create the test data on Reddit.

**Instructions:**

1.  **Log in to Reddit:** Use a dedicated Reddit account (the "test creator" account) to perform the following actions.
2.  **Create Test Posts:** On the `/r/argentina_dev` subreddit, create four separate link posts. Each post will have a simple title (e.g., "Test Post for Infobae") and will link to one of the following URLs:
    *   **Infobae Post:** A recent news article from `infobae.com`.
    *   **La Nacion Post:** A recent news article from `lanacion.com.ar`.
    *   **X/Twitter Post:** A tweet from `x.com`.
    *   **YouTube Post:** A short (under 5 minutes) video from `youtube.com`.
3.  **Document URLs:** After creating the posts, save their full Reddit URLs. These URLs will be hardcoded into the test suite as constants.

---

### Section 3: Test Implementation Strategy

A new test file, `tests/test_e2e_live.py`, will be created. It will contain the logic for the E2E tests.

**General Workflow for Each Test:**

1.  **Test Setup:**
    -   The test function will start by ensuring the local CanillitaBot instance is running.
    -   It will initialize the `praw` Reddit client using a dedicated "tester" account (this can be the same as the "test creator" account). This account's credentials will be stored in the `.env` file.

2.  **Trigger and Poll:**
    -   The test will use the pre-recorded URL to fetch the specific Reddit submission to be tested.
    -   It will enter a polling loop (e.g., check every 10 seconds for up to 2 minutes) to wait for new comments to appear on the submission.

3.  **Verification and Assertion:**
    -   Once a new comment is detected, the test will check if the comment's author is the `CanillitaBot`.
    -   If the author matches, the test will retrieve the comment body.
    -   A series of `assert` statements will be used to validate the comment's content against the expected format and keywords for that link type.
    -   If the bot does not comment within the timeout period, the test will fail.

---

### Section 4: Detailed Test Cases

#### Test Case 1: Infobae Article Summary

*   **Objective:** Verify that the bot correctly summarizes and posts a comment for an `infobae.com` article.
*   **Implementation Steps:**
    1.  Define a test function `test_infobae_summary()`.
    2.  Use the URL of the pre-created Infobae Reddit post.
    3.  Implement the polling logic to wait for the bot's comment.
    4.  Assert the following conditions on the comment body:
        -   `assert "Fuente: infobae.com" in comment.body`
        -   `assert "Este es un resumen hecho por un bot..." in comment.body`
        -   `assert len(comment.body) > 150` (to ensure a summary was generated).

#### Test Case 2: La Nacion Article Summary

*   **Objective:** Verify that the bot correctly summarizes and posts a comment for a `lanacion.com.ar` article.
*   **Implementation Steps:**
    1.  Define a test function `test_lanacion_summary()`.
    2.  Use the URL of the pre-created La Nacion Reddit post.
    3.  Implement the polling logic.
    4.  Assert the following conditions on the comment body:
        -   `assert "Fuente: lanacion.com.ar" in comment.body`
        -   `assert "Este es un resumen hecho por un bot..." in comment.body`
        -   `assert len(comment.body) > 150`.

#### Test Case 3: X/Twitter Post Formatting

*   **Objective:** Verify that the bot correctly formats and posts a comment for an `x.com` tweet.
*   **Implementation Steps:**
    1.  Define a test function `test_x_twitter_post()`.
    2.  Use the URL of the pre-created X/Twitter Reddit post.
    3.  Implement the polling logic.
    4.  Assert the following conditions on the comment body:
        -   `assert "Tweet de @" in comment.body`
        -   `assert "Este es un resumen hecho por un bot..." in comment.body`
        -   Check for the presence of the original tweet text within the comment.

#### Test Case 4: YouTube Video Summary

*   **Objective:** Verify that the bot correctly generates and posts a summary for a YouTube video.
*   **Implementation Steps:**
    1.  Define a test function `test_youtube_summary()`.
    2.  Use the URL of the pre-created YouTube Reddit post.
    3.  Implement the polling logic.
    4.  Assert the following conditions on the comment body:
        -   `assert "Resumen para el vago:" in comment.body`
        -   `assert "Este es un resumen hecho por un bot..." in comment.body`
        -   `assert len(comment.body) > 100` (to ensure the summary is not empty).

---

### Section 5: Tooling and Execution

-   **Configuration:** The `.env` file will be updated to include credentials for the "tester" Reddit account (e.g., `TESTER_REDDIT_CLIENT_ID`, `TESTER_REDDIT_CLIENT_SECRET`, etc.).
-   **Makefile:** A new target will be added to the `Makefile`:
    ```makefile
    test-e2e:
        @echo "Running live E2E tests..."
        @docker compose run --rm test pytest -v tests/test_e2e_live.py
    ```
-   **Execution:** The test suite will be run by executing `make test-e2e` from the command line.
