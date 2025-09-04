# Plan for CanillitaBot Improvements

Here is a list of proposed changes to improve the project's structure, simplify the development workflow, and enhance the testing and deployment processes.

### Section 1: Refactor Dockerfile and docker-compose.yml for better development and production separation

-   **Refactor Dockerfile:**
    -   Create a `development` stage that installs all dependencies from `requirements.txt` and development tools.
    -   Create a `production` stage that only installs production dependencies.
    -   Ensure the `development` stage uses a volume for the source code to allow for live reloading.
    -   Ensure the `production` stage copies the source code into the image.

-   **Refactor docker-compose.yml:**
    -   Create a `docker-compose.dev.yml` for development that uses the `development` build target and mounts the source code.
    -   Update the main `docker-compose.yml` to be production-focused, using the `production` build target.
    -   Add a `test` service to run the test suite in a container.

### Section 2: Improve Makefile and add a test command

-   Add a `test` target to the `Makefile` that runs the test suite using the new `test` service in `docker-compose.dev.yml`.
-   Update the `health` target to run inside a container to ensure a consistent environment.
-   Add linting and formatting targets (`lint`, `format`) to the `Makefile`.

### Section 3: Enhance the test suite

-   Review the existing tests and fix any failing tests.
-   Add unit tests for critical components like the `ContentProcessor` and `ArticleExtractor`.
-   Add integration tests for the Reddit and Gemini clients to ensure they work correctly with the live APIs (can be disabled by default).
-   Use mocking to isolate components during testing.

### Section 4: Simplify the deployment process

-   Replace the custom `deploy` script in the `Makefile` with a more robust solution.
-   Use a container registry (like Docker Hub or GitHub Container Registry) to store the production image.
-   Update the deployment process to pull the image from the registry and run it. This will be simpler and more reliable than the current `docker save` and `scp` method.
-   Alternatively, for simplicity, we can keep the current deployment method but improve the script to be more robust.