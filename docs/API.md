# API Reference

Base URL (via load balancer): `http://localhost:8080`
Interactive Swagger UI: `http://localhost:8080/docs` · ReDoc: `http://localhost:8080/redoc`

All `POST`/`PATCH` bodies are JSON. Authenticated endpoints require:
`Authorization: Bearer <access_token>`.

---

## Auth

### `POST /api/v1/auth/signup`
Create an account and receive tokens immediately.

```json
// request
{ "email": "ada@example.com", "password": "supersecret123", "full_name": "Ada Lovelace" }

// 201 response
{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }
```
`409` if the email is already registered. `422` on validation failure (password < 8 chars, malformed email).

### `POST /api/v1/auth/login`
```json
// request
{ "email": "ada@example.com", "password": "supersecret123" }
```
`200` with the same token shape as signup. `401` on bad credentials.

### `GET /api/v1/auth/me`
Returns the authenticated user's profile. `401` without a valid token.

---

## URLs

All endpoints below require authentication and operate only on URLs owned
by the caller.

### `POST /api/v1/urls`
Create a short URL. Rate-limited to **30 requests / 60s per user** (sliding window, see `ARCHITECTURE.md` §9.2).

```json
// request
{
  "target_url": "https://example.com/some/very/long/path",
  "custom_alias": "my-link",       // optional, alphanumeric, 3-64 chars
  "expires_at": "2026-12-31T00:00:00Z",  // optional, ISO 8601
  "title": "My link"               // optional
}
```
```json
// 201 response
{
  "id": 42,
  "short_code": "4c94",
  "custom_alias": "my-link",
  "target_url": "https://example.com/some/very/long/path",
  "title": "My link",
  "created_at": "2026-06-20T14:11:09Z",
  "expires_at": "2026-12-31T00:00:00Z",
  "is_active": true,
  "total_clicks": 0,
  "short_url": "http://localhost:8080/my-link"
}
```
- `409` if `custom_alias` is already taken.
- `422` if `target_url` doesn't start with `http://`/`https://`, or `custom_alias` isn't alphanumeric.
- `429` if the rate limit is exceeded.

### `GET /api/v1/urls`
List the caller's URLs. Query params:

| Param | Type | Default | Notes |
|---|---|---|---|
| `page` | int | 1 | 1-indexed |
| `page_size` | int | 10 | max 100 |
| `search` | string | — | matches target URL, short code, alias, or title (`ILIKE`) |
| `is_active` | bool | — | filter by active/deactivated |

Returns `{ items, total, page, page_size, total_pages }`.

### `GET /api/v1/urls/{url_id}`
Fetch a single URL by its numeric ID. `404` if not found or not owned by the caller.

### `PATCH /api/v1/urls/{url_id}`
Partial update — any subset of `target_url`, `expires_at`, `is_active`, `title`. Invalidates and (if reactivated) repopulates the Redis cache entry for both the old and new effective code.

### `DELETE /api/v1/urls/{url_id}`
`204` on success. Invalidates the cache entry first, then deletes (and cascades to its click events / daily stats via FK `ON DELETE CASCADE`).

---

## Redirect

### `GET /{code}`
**Not** under `/api/v1` — short links are clean root-level paths, e.g. `http://localhost:8080/4c94`.

- Resolves `code` against `short_code` OR `custom_alias`.
- Cache-aside: Redis first, Postgres on miss (and repopulates Redis).
- `302` redirect to the target URL on success.
- `404` if no such code exists.
- `410 Gone` if the link is deactivated or past its `expires_at`.
- `429` if the per-IP sliding-window rate limit (100 req/60s) is exceeded.
- Publishes a click event to RabbitMQ asynchronously — this never blocks or fails the redirect itself.

---

## Analytics

### `GET /api/v1/analytics/summary`
Dashboard summary for the authenticated user: `total_urls`, `total_clicks`, `clicks_today`, `top_urls` (top 5 by clicks), `daily_clicks` (last 14 days, aggregated across all owned URLs).

### `GET /api/v1/analytics/urls/{url_id}?days=30`
Per-URL analytics: `total_clicks`, `daily_clicks` (last `days`, default 30, max 365), `top_referrers`, `top_countries` (mocked geo — see `SYSTEM_DESIGN_DECISIONS.md`).

---

## Architecture / Observability

These endpoints are **not** authenticated — they expose only aggregate
system metrics, no user data — and power the frontend's Architecture page.

### `GET /api/v1/architecture/metrics`
```json
{
  "cache": { "hits": 184, "misses": 12, "hit_rate": 0.9388 },
  "queue": { "queue_depth": 0, "dlq_depth": 0, "processed_events": 196 },
  "workers": [
    { "worker_id": "worker-1", "last_heartbeat_seconds_ago": 2.1, "alive": true }
  ],
  "db_pool_size": 20,
  "db_pool_checked_out": 1
}
```

### `GET /api/v1/health`
Aggregate dependency health: `{ "status": "healthy" | "degraded", "checks": { "database": "up", "redis": "up" } }`.

### `GET /api/v1/health/live`
Liveness probe — process is up. No dependency checks. Use for container orchestrator liveness probes.

### `GET /api/v1/health/ready`
Readiness probe — verifies DB and Redis are actually reachable. Use for orchestrator readiness probes / load balancer health checks.

---

## Error format

All errors return:
```json
{ "detail": "human-readable message" }
```
or, for request validation errors (`422`):
```json
{ "detail": [ { "type": "...", "loc": ["body", "field"], "msg": "...", "input": "..." } ] }
```

## Rate limit headers

Rate-limited endpoints currently signal limits via the `429` status and
message body rather than `X-RateLimit-*` response headers. Adding those
headers is a natural follow-up (see `DEPLOYMENT.md` → Known limitations).
