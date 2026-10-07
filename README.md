# SmartDesk AI

AI-powered help desk and customer support SaaS platform.

Production-quality portfolio project demonstrating full-stack engineering,
SaaS multi-tenancy, AI integration, data engineering, security, testing,
and DevOps.

## Stack

- **Frontend:** Next.js, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query,
  React Hook Form, Zod
- **Backend:** FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2
- **Database:** PostgreSQL 16 + pgvector
- **Cache / Queue:** Redis 7
- **AI:** OpenAI API, embeddings, pgvector, RAG, structured outputs
- **Infra:** Docker, Docker Compose, GitHub Actions

## Repo layout

```
frontend/       Next.js app (runs locally with npm run dev)
backend/        FastAPI app (Docker or local venv)
infrastructure/ Docker Compose + init scripts
docs/           Architecture and ADRs
```

## Prerequisites

- Docker + Docker Compose
- Node.js 20+
- Python 3.12+ (only if running the backend outside Docker)
- `make` (optional)

## Local setup

### 1. Clone and configure env

```bash
git clone <your-fork> smartdesk-ai
cd smartdesk-ai

cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

The defaults in `.env.example` are safe for local development.
**Never commit real `.env` files or secrets.**

### 2. Start backend, Postgres, and Redis

```bash
cd infrastructure
docker compose up --build
```

This starts:

- PostgreSQL (with `vector`, `pg_trgm`, `uuid-ossp` extensions) on `:5432`
- Redis on `:6379`
- FastAPI on `:8000`

Verify:

- Liveness: <http://localhost:8000/api/v1/health>
- Readiness (DB + Redis): <http://localhost:8000/api/v1/health/ready>
- OpenAPI docs: <http://localhost:8000/api/v1/docs>

### 3. Run migrations

```bash
docker compose exec backend alembic upgrade head
```

There are no models yet in Phase 1, so this is a no-op, but it validates
that Alembic is wired correctly.

### 4. Start the frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

## Running checks

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
mypy app
pytest
```

Or inside Docker:

```bash
cd infrastructure
docker compose exec backend ruff check .
docker compose exec backend pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

## Environment variables

Backend reads `backend/.env` (see `backend/.env.example`).
Frontend reads `frontend/.env.local` (see `frontend/.env.example`).

Key variables:

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` / `staging` / `production` / `test` |
| `APP_DEBUG` | Enables SQL echo and verbose errors |
| `LOG_JSON` | `true` for JSON logs (production), `false` for pretty (dev) |
| `CORS_ORIGINS` | JSON array of allowed origins |
| `POSTGRES_*` | Database connection |
| `REDIS_*` | Cache / queue connection |
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL the browser calls |

## Roadmap

- **Phase 1 (this):** Foundation — repo, config, logging, DB/Redis, Alembic, health checks
- **Phase 2:** Identity and multi-tenancy (organizations, users, memberships, RBAC)
- **Phase 3:** Ticket core (tickets, categories, priorities, assignment, teams)
- **Phase 4:** Conversations, attachments, SLA, notifications
- **Phase 5:** Customers, settings, audit logs
- **Phase 6:** Knowledge base + full-text + semantic search
- **Phase 7:** AI assistive features (classification, priority, summarization, replies)
- **Phase 8:** RAG assistant
- **Phase 9:** Analytics
- **Phase 10:** Hardening and portfolio polish