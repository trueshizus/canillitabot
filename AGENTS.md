# Repository Guidelines

## Project Structure & Modules
- `src/`: Python source code
  - `core/` bot lifecycle, config, DB, processing
  - `clients/` integrations (e.g., Reddit, Gemini, YouTube)
  - `extractors/` article parsing and provider-specific logic
  - `shared/` utilities and queue helpers
  - `services/` small service endpoints (e.g., health)
  - `dashboard/` Flask dashboard (`static/`, `templates/`, `app.py`)
- `tests/`: pytest suite (`test_*.py`)
- `tools/`: local developer scripts
- `config/`: runtime configuration (read-only in containers)
- `data/`, `logs/`: runtime volumes
- Entrypoints: `run.py`, `docker-compose.yml`, `Makefile`

## Build, Test, and Development
- `make build`: Build Docker images.
- `make up` / `make stop`: Start/stop full stack (bot, Redis, dashboard).
- `make test`: Run pytest in the isolated test service.
- `make health`: Quick config/DB checks.
- Local run: `./venv/bin/python run.py` (ensure `.env` is configured).
- Dashboard: `docker compose up dashboard` (served on port 9000).

## Deployment
- Environment: DigitalOcean droplet reachable via SSH alias `bot` (configure in your `~/.ssh/config`).
- Deploy: `make deploy` runs remotely: `cd <REMOTE_DIR> && git fetch && git checkout <BRANCH> && git pull --rebase --autostash && make build && make up && make health`.
- Overrides: `HOST=my-alias`, `REMOTE_DIR=/path/to/canillitabot`, `BRANCH=main` (default branch is `master`).

## Coding Style & Naming
- Python 3.12, 4‑space indentation, PEP 8.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Type hints encouraged in new/edited code.
- Format/lint (available in builder image): `black .`, `flake8`, optional `mypy`.
- Keep files focused; prefer small modules (see `core/` refactors).

## Testing Guidelines
- Framework: `pytest`.
- Location: place tests under `tests/` named `test_*.py` mirroring module paths.
- Run: `make test` or `docker compose run --rm test pytest -v`.
- Include realistic cases using `.env.example` patterns and Redis URL stubs.

## Commit & Pull Request Guidelines
- Prefer Conventional Commits: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:` with optional scope, e.g., `refactor(core): split processor`.
- Messages: imperative, concise, explain why + what.
- PRs: clear description, linked issues, test coverage for changes, `make test` passing, screenshots/GIFs for dashboard UI changes, note config or migration steps.

## Security & Configuration Tips
- Copy `.env.example` to `.env`; never commit secrets.
- Key vars: `REDIS_URL`, API keys for external clients.
- `config/` is mounted read‑only; prefer env vars for secrets.
- Use `make health` before deploy; deploy via `make deploy` (SSH alias `bot`) or `make deploy HOST=my-alias`.
