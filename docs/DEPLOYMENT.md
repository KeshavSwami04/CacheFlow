# Deployment Guide

## Local development (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
```

This brings up: `postgres`, `redis`, `rabbitmq`, two API replicas
(`backend_1`, `backend_2`), the `lb` (nginx load balancer in front of
them), one `worker`, and the `frontend` (built and served by nginx).

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:3000 | SPA; proxies `/api/*` to `lb` |
| API (via LB) | http://localhost:8080 | what `SHORT_URL_BASE` points at |
| Swagger / ReDoc | http://localhost:8080/docs / `/redoc` | |
| RabbitMQ management | http://localhost:15672 | user/pass from `.env` (`cacheflow`/`cacheflow` by default) |
| Postgres | localhost:5432 | exposed for local psql access |
| Redis | localhost:6379 | exposed for local `redis-cli` access |

First boot runs `init-db/init.sql` automatically (via
`docker-entrypoint-initdb.d`) against a fresh `postgres_data` volume —
nothing else to migrate manually for a clean start.

### Running without Docker (for backend development)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# point at locally running postgres/redis/rabbitmq, e.g.:
export POSTGRES_HOST=localhost REDIS_HOST=localhost RABBITMQ_HOST=localhost

uvicorn app.main:app --reload --port 8000
# in another terminal:
python -m app.workers.main
```

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api to http://localhost:8000 (see vite.config.ts)
```

---

## Environment variables

See [`.env.example`](../.env.example) for the full list with defaults.
Notable ones:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing secret — **must** be changed for any non-local deployment |
| `SHORT_URL_BASE` | The public-facing host short links are generated against |
| `URL_CACHE_TTL_SECONDS` | Redis TTL for cached URL lookups |
| `RATE_LIMIT_*` | Sliding-window limits for create/redirect endpoints |
| `OTEL_ENABLED` / `OTEL_EXPORTER_OTLP_ENDPOINT` | Enable tracing export to a collector (Jaeger/Tempo/etc.) |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins |

---

## Scaling

### API tier
The API is stateless (JWT auth, no server-side sessions), so it scales by
adding replicas behind `lb`. The compose file ships with two
(`backend_1`, `backend_2`) explicitly defined so the load-balancing
behavior is visible and deterministic locally. To add more:

1. Add `backend_3`, `backend_4`, ... services in `docker-compose.yml` (copy `backend_1`'s block).
2. Add matching `server backend_3:8000;` lines to `nginx/lb.conf`'s upstream block.
3. `docker compose up -d --build`.

In a cloud deployment, replace `lb` with a managed load balancer (ALB,
GCLB, etc.) pointed at an autoscaling group / Kubernetes Service of API
pods — the application code doesn't change either way, because it was
written stateless from the start.

### Worker pool
Workers are RabbitMQ competing consumers on the same queue — scale them
independently of the API:

```bash
docker compose up -d --scale worker=4
```

No coordination needed between worker replicas; RabbitMQ distributes
messages round-robin to whichever consumer is free (subject to
`WORKER_PREFETCH_COUNT`).

### Database
Postgres is a single instance in this setup — the realistic next step
once read query volume grows is read replicas for analytics/dashboard
queries (see `SYSTEM_DESIGN_DECISIONS.md`). Not implemented here, by
design — it's documented as the next step rather than built speculatively.

---

## Observability

- **Structured logs**: every API process emits JSON logs (set `LOG_JSON=true`) with a `request_id` bound to every line for a given request — grep/filter by it in your log aggregator of choice.
- **OpenTelemetry**: set `OTEL_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT=http://your-collector:4318/v1/traces` to export traces for the FastAPI app, SQLAlchemy queries, and Redis calls. Without an endpoint configured, instrumentation still runs but spans aren't exported anywhere — safe to enable locally with no collector running.
- **Health checks**: `/api/v1/health/live` (liveness) and `/api/v1/health/ready` (readiness) are wired into each Dockerfile's `HEALTHCHECK` and are the right targets for Kubernetes liveness/readiness probes too.
- **Architecture Dashboard**: `/api/v1/architecture/metrics` (and the frontend's `/architecture` page) for live cache/queue/worker/DB-pool visibility — point your uptime monitoring at this if you want a single endpoint to assert "the whole pipeline is healthy," not just "the process is up."

---

## Production hardening checklist

This project intentionally optimizes for demonstrating system design
clearly over being deployment-ready out of the box. Before running this
anywhere real:

- [ ] Replace `SECRET_KEY` with a long random value from a secrets manager, not `.env`.
- [ ] Put TLS in front of `lb` and `frontend` (terminate at a cloud LB or add `nginx` TLS config).
- [ ] Rotate RabbitMQ/Postgres credentials out of `.env` into your platform's secret store.
- [ ] Add Alembic migrations in place of `init-db/init.sql` for an evolving schema (the SQLAlchemy models are already migration-ready).
- [ ] Add `X-RateLimit-*` response headers and consider a global per-IP limit in front of auth endpoints (currently only `create` and `redirect` are rate-limited).
- [ ] Swap the mocked geo lookup for a real GeoIP provider if geographic analytics need to be accurate rather than illustrative.
- [ ] Add a scheduled job to deactivate/sweep expired URLs (the partial index on `expires_at` is already there for it) — currently expiry is checked lazily at redirect time only.
- [ ] Point `OTEL_EXPORTER_OTLP_ENDPOINT` at a real collector and wire up alerting on the Architecture Dashboard's underlying metrics (DLQ depth > 0, worker count == 0, cache hit rate dropping).
