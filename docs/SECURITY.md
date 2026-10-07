# SmartDesk AI — Security Model

This document describes how SmartDesk AI protects data and prevents abuse.
It is written for engineers, security reviewers, and operators.

---

## Authentication

**Passwords**
- Hashed with **Argon2id** (`argon2-cffi`, defaults from the library).
- Minimum 12 characters, must contain letters and digits, blocklist check.
- Plaintext passwords never leave the request, are never logged, and are
  never persisted.

**Access tokens**
- Signed JWTs, `HS256`, 15-minute expiry by default.
- Claims: `sub` (user id), `type` (`access`), `iat`, `exp`.
- The signing key comes from `JWT_SECRET_KEY`. In `APP_ENV=production`
  the settings layer refuses to boot with the dev default.

**Refresh tokens**
- Opaque 48-byte URL-safe strings, never JWTs.
- Stored as SHA-256 hashes in `refresh_tokens`. The raw token is returned
  to the client once.
- **Rotated on every use.** Replaying a used refresh token is rejected
  and the session is invalidated.
- Revocable independently of the access token: rows carry `revoked_at`.

**Rate limits on auth**
- `POST /auth/login` — 10 requests per minute per identity.
- `POST /auth/register` — 5 per hour per identity.
- `POST /auth/refresh` — 30 per minute per identity.
- Exceeded limit → `429 Too Many Requests` with `retry_after_seconds`.

---

## Authorization

Authorization is enforced server-side in dependency-injected guards. The
frontend reuses the same guards for navigation, but hiding a button is
never the guard.

**Roles**
- `ADMIN` — full organization management.
- `AGENT` — ticket operations, AI copilot, KB search.
- `CUSTOMER` — their own tickets, their own notifications.

**Guards**
- `require_admin` — only `ADMIN`.
- `require_staff` — `ADMIN` or `AGENT`.
- `require_customer` — only `CUSTOMER` (used for customer-only routes).

**Read/write access on tickets**
- Staff can read and write any ticket in their organization.
- Customers can only read tickets whose `customer.email` matches their
  own email. Cross-tenant and cross-customer access returns **404**, not
  **403**, so the existence of another ticket is not disclosed.

**Guardrails**
- An admin cannot demote or deactivate their own account.
- Only admins can delete tickets, teams, categories, SLAs, or trigger a
  full reindex.

---

## Tenant isolation

Every tenant-owned table carries an `organization_id` column. The
following invariant holds everywhere:

> **Every query that reads or mutates a tenant-owned row filters by
> `organization_id` at the SQL level.**

**How it is enforced**
- Repository methods accept `org_id` as a required argument. There is no
  unscoped `list()` or `get(id)` on tenant tables.
- Services derive `org_id` from `current_user.organization_id` — never
  from the request body, query string, or headers.
- Test suites assert that cross-tenant reads return 404 and cross-tenant
  lists exclude other orgs' rows.

**Where the client is ignored**
- If a client sends `organization_id` in a body, header, or query string,
  it is ignored. The schema does not include it; the endpoints do not
  read it.

**Vectors**
- Vector search on `knowledge_chunks` includes
  `WHERE organization_id = :org_id` inside the query, before ranking. A
  chunk from another org is never a candidate.

**Notifications**
- Scoped by both `organization_id` **and** `user_id`. A user cannot read
  or mutate another user's notifications, even within the same org.

---

## AI security

**Prompt injection**
- User-supplied fields (ticket title, description, comments, customer
  name) are wrapped in explicit `BEGIN UNTRUSTED CONTENT` markers and
  common injection markers are neutralized.
- System prompts state that anything inside those markers is data, never
  instructions.
- Model outputs are validated against Pydantic schemas. Free-form
  strings have length caps and required fields.

**Model and provider isolation**
- The API key lives only in the backend environment. It is never sent to
  the browser and never returned in an API response.
- Every AI call is logged with `operation`, `model`, latency, token
  counts, and a truncated `prompt_hash`. Prompts and completions are not
  logged.

**RAG**
- Retrieval filters by `organization_id` **and** `article.status =
  PUBLISHED` in the same SQL statement as the similarity ranking.
- The model is given a numbered source list; returned citations are
  filtered against that list. Out-of-range citations are dropped, and if
  none survive, the response is downgraded to `is_grounded: false`.
- When retrieval returns nothing above the similarity threshold, the
  service returns a fixed "not enough evidence" response **without
  calling the model.** This is the primary anti-hallucination guard.
- Attachments are not currently embedded. When they are, the same
  organization filter applies.

---

## Data protection

**In transit**
- TLS is terminated at the load balancer in production. Locally the app
  runs over HTTP; `docs/` describes the deployment topology.

**At rest**
- Passwords: Argon2id hashes.
- Refresh tokens: SHA-256 hashes.
- Object storage: server-side encryption enabled at the bucket level in
  production (no app changes required).

**PII**
- The API does not currently implement a formal data-classification
  scheme. Logs include ids and event metadata, never bodies or message
  text. If you add analytics pipelines that process customer messages,
  document them here and gate them behind organization consent.

**Secrets**
- `.env` files are gitignored. `.env.example` contains only safe defaults.
- The dev JWT secret is guarded: booting with `APP_ENV=production` and
  the dev default raises at startup.
- Production deployments read secrets from the platform's secret manager.

---

## Rate limiting

Rate limiting is a Redis-backed sliding window. Each route family has
its own limit. Identity is `Authorization` token (hashed) if present,
otherwise client IP.

| Scope | Limit | Window |
|---|---|---|
| `auth:login` | 10 | 60s |
| `auth:register` | 5 | 3600s |
| `auth:refresh` | 30 | 60s |
| `ai:generate` | 30 | 60s |
| `ai:search` | 60 | 60s |
| `ai:ask` | 20 | 60s |
| `ai:reindex` | 2 | 3600s |
| `attachments:upload` | 20 | 60s |

**Failure mode.** If Redis is unavailable, requests are allowed. This is
deliberate: losing auth is worse than a brief window of reduced rate
limiting. Redis availability is a critical dependency tracked in
`docs/architecture.md`.

**What is not yet rate limited**
- `GET /tickets` and other read-heavy endpoints. Read paths are protected
  by pagination caps and database indexes. If you observe scraping in
  practice, add `rate_limit("tickets:list", 120, 60)` to those routes.

---

## File security

**Uploads**
- Hard cap: 25 MiB per file.
- Allowlist: PNG, JPEG, GIF, WebP, PDF, TXT, CSV, ZIP, DOCX, XLSX.
- Every upload is validated on three axes: declared MIME type,
  extension, and **magic bytes**. A file claiming to be PNG must start
  with `\x89PNG`. A PHP script with a `.png` name fails.
- Filenames are never used as storage keys. Every file is stored under
  an opaque UUID path scoped by `organization_id` and `ticket_id`.
- The client-supplied filename is preserved only as metadata
  (`file_name`), never as a filesystem path.

**Downloads**
- Downloads must pass the same read-access checks as the parent ticket.
- The filesystem path is never returned to the client. In production
  this endpoint issues a short-lived presigned URL from object storage.

**Not yet implemented**
- Antivirus scanning. The `TicketAttachment` model has no `scan_status`
  column, but the object storage integration should add one. Until then,
  treat uploads as untrusted and do not auto-render them inline in the UI.

**Content-Disposition**
- When serving downloads directly, always use
  `Content-Disposition: attachment; filename="..."`. Never `inline` for
  user uploads — that would allow inline HTML/JS rendering.

---

## Other controls

**SQL injection.** All queries use SQLAlchemy's parameter binding. The
only dynamically composed SQL fragment is the `date_trunc` granularity
in analytics, which is validated by a route-level regex allowlist
(`^(day|week|month)$`) before the request reaches the repository.

**XSS.** The frontend renders all user content through React, which
escapes interpolated text. There is no `dangerouslySetInnerHTML` in the
codebase. Knowledge-base article bodies, if rendered as Markdown in a
future phase, must go through a sanitizer (e.g. DOMPurify) with a strict
allowlist.

**Mass assignment.** All request schemas enumerate fields explicitly.
There is no `**payload` splatting into ORM constructors.

**Unvalidated input.** All request bodies, query parameters, and path
parameters are typed with Pydantic. Invalid input fails with a
consistent 422 shape.

**Logging.** Structured logs carry ids, event names, and durations.
Passwords, tokens, and message bodies are never logged. AI prompts are
represented by a truncated hash, not their text.

**CSRF.** The API uses bearer tokens in an `Authorization` header, which
CSRF cannot exploit. If cookie-based sessions are introduced later, add
double-submit CSRF tokens and set `SameSite=Strict` on session cookies.

---

## Reporting a vulnerability

Email `security@smartdesk.example` with a description and, if possible,
a minimal reproducer. Do not open a public issue. We aim to acknowledge
reports within two business days.