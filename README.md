# AI Customer Support Resolution Platform

A production-style AI customer support platform. Tickets are classified, investigated with RAG and tools, verified, and answered with citations. Progress streams to the UI, and every AI run is recorded for audit and evaluation.

> Demo project using publicly available GitLab documentation as its knowledge corpus. Not affiliated with GitLab.

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query |
| Backend | FastAPI, Pydantic, SQLAlchemy (async), Alembic |
| Data | PostgreSQL 16 + pgvector, Redis 7 |
| Worker | Python background process (shares the backend image) |
| Tooling | uv, ruff, pytest, ESLint, Docker Compose, GitHub Actions |

## Project structure

```text
backend/     FastAPI app (app/), Alembic migrations (alembic/), tests
worker/      Background worker (imports backend code from app/)
frontend/    React + Vite app
evals/       Evaluation datasets and runs
data/        raw/ and processed/ (gitignored), generated/ (tracked)
docs/        Architecture and design notes
scripts/     Utility scripts
```

## Getting started (Docker)

Prerequisites: Docker Desktop.

1. Create the env files:

   ```bash
   cp .env.example backend/.env
   echo "VITE_API_BASE_URL=http://localhost:8000" > frontend/.env
   ```

2. Build and start everything (from the repo root):

   ```bash
   docker compose up -d --build
   ```

   Startup order: `postgres` + `redis` healthy → `migrate` runs `alembic upgrade head` and exits → `api` + `worker` start → `frontend` starts.

3. Open:

   | Service | URL |
   |---|---|
   | Frontend | http://localhost:5173 |
   | API | http://localhost:8000 |
   | API docs (Swagger) | http://localhost:8000/docs |
   | Liveness | http://localhost:8000/health |
   | Readiness (Postgres + Redis) | http://localhost:8000/health/ready |

`migrate` showing **Exited (0)** is expected. It is a one-off job.

### Useful commands

```bash
docker compose ps -a              # status of all services
docker compose logs -f api        # follow API logs
docker compose run --rm migrate   # apply migrations only
docker compose down               # stop (keeps data)
docker compose down -v            # stop and delete database/Redis data
```

## Local development (app outside Docker)

Run only Postgres and Redis in Docker, and the app on your machine. In `backend/.env`, use `localhost` instead of the container hostnames:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/customer_support
REDIS_URL=redis://localhost:6379/0
```

```bash
docker compose up -d postgres redis

# Backend (from backend/)
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend (from frontend/)
npm install
npm run dev
```

Inside Docker, `docker-compose.yml` overrides `DATABASE_URL` and `REDIS_URL` with the container hostnames, so the same `backend/.env` works for both.

## Environment variables

See [`.env.example`](.env.example). Real `.env` files are gitignored. Never commit them.

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | backend, worker, migrate | Postgres connection (`postgresql+asyncpg://...`) |
| `REDIS_URL` | backend, worker | Redis connection |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | reference | Postgres credentials |
| `ENVIRONMENT` | backend | `development` / `production` |
| `LOG_LEVEL` | backend, worker | Logging level (default `INFO`) |
| `CORS_ORIGINS` | backend | Allowed frontend origins (JSON list) |
| `VITE_API_BASE_URL` | frontend | API base URL (goes in `frontend/.env`) |
| `OPENAI_API_KEY` | later phases | LLM access |

## Database migrations

```bash
# from backend/
uv run alembic revision -m "describe change"
uv run alembic upgrade head
```

With Docker, migrations run automatically on `docker compose up` (the `migrate` service).

## Demo data

Seeds two organizations (Acme Software, Globex Engineering) with an admin, a support agent and two customers each, sample tickets with messages and events, and knowledge-source document metadata. Safe to run repeatedly.

```bash
# from backend/
uv run python -m app.db.seed

# or with Docker
docker compose run --rm api python -m app.db.seed
```

Seeded users have no usable password until authentication is implemented.

## Checks and CI

```bash
# Backend (from backend/)
uv run ruff check . ../worker
uv run pytest

# Frontend (from frontend/)
npm run lint
npm run build
```

GitHub Actions (`.github/workflows/ci.yml`) runs these on every push and pull request.

## Roadmap

- [x] Phase 1: Repository and project foundation
- [ ] Phase 2: Database design
- [ ] Phase 3: Authentication and authorization
- [ ] Knowledge ingestion, RAG, agents, async jobs, evaluation, deployment
