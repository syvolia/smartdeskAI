# SmartDesk AI — Architecture (Phase 1 baseline)

## Shape

Modular monolith. Clean module boundaries, but a single deployable API for now.
Runtimes:

- Next.js (frontend)
- FastAPI (backend API)
- PostgreSQL + pgvector (data)
- Redis (cache, rate limiting, queues, pub/sub)
- Background worker (added in a later phase)

## Backend module boundaries
- routers → HTTP only, thin
- services → business rules, orchestration, transactions
- repositories → tenant-scoped data access
- models → SQLAlchemy ORM
- schemas → Pydantic request/response contracts
- core → config, logging, exceptions, permissions
- db → engine, session, base
- ai → provider adapters, prompts, RAG (later phase)
- workers → background jobs (later phase)


## Tenancy

Shared schema, `org_id` on every tenant-owned table. Tenant context is
resolved from the authenticated membership, never trusted from the client.
Repositories require `org_id`. Row-Level Security is planned as a second
layer in Phase 9.

## Errors

All expected errors raise `AppError` subclasses. Handlers convert them into
`{"error": {"code", "message", "details"}}`. Validation errors use the same
shape. Unhandled exceptions log with a stack trace and return a generic
`internal_error`.

## Logging

Structlog with request-scoped context (`request_id`, `method`, `path`).
Development renders pretty console; production renders JSON.

## Health

- `GET /api/v1/health` — liveness, always 200 if the process is up.
- `GET /api/v1/health/ready` — readiness, verifies Postgres and Redis;
  returns 503 when a dependency is unavailable.

## Config

All configuration flows through `app.core.config.Settings` (pydantic-settings).
No secrets are hardcoded. `.env` files are local only; production must supply
secrets via environment variables or a secret manager.

## Next phase

Phase 2 adds identity and multi-tenancy: `organizations`, `users`,
`memberships`, `roles`, `permissions`, sessions, invitations, and
tenant-isolation test coverage.