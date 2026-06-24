# System Design Decisions

This is the document to read before a system design interview about this
project — it explains *why*, not just *what*.

---

## Why Redis?

Redis sits in two distinct roles, and it's worth separating them:

1. **Cache-aside for redirect resolution.** The redirect path
   (`GET /{code}`) is, by a wide margin, the highest-traffic endpoint in
   any URL shortener — reads outnumber writes by orders of magnitude.
   Hitting Postgres on every redirect would mean every click pays for a
   network round-trip + index lookup + connection-pool contention, all on
   the path the *visitor* is waiting on. Redis turns the common case into
   an in-memory key lookup (`url:{code}` → JSON blob), which is what makes
   sub-millisecond redirects realistic at scale.

2. **Sliding-window rate limiting.** Rate limiting needs shared,
   low-latency, atomic counters visible to *every* API replica — an
   in-process counter wouldn't work once there's more than one backend
   instance. Redis's sorted sets + Lua scripting give us atomic
   read-trim-count-admit in one round trip, which a naive
   `INCR`-with-`EXPIRE` fixed-window approach can't do without the
   boundary-burst problem (2x traffic at window edges).

**Why not just cache in the application process (e.g., an in-memory
LRU)?** Because the API is horizontally scaled (see Scaling Strategy
below) — an in-process cache would be inconsistent across replicas (a
write on replica A wouldn't invalidate replica B's stale entry) and
wouldn't survive a replica restart. A shared external cache is the only
option once you have more than one API instance, which you need anyway
for availability.

---

## Why RabbitMQ?

The core tension in a URL shortener's analytics: you want every click
recorded, but you *cannot* let recording it slow down or risk the
redirect itself. These are two different reliability/latency
requirements glued onto the same event, which is exactly the case for
decoupling them with a message broker:

- The redirect endpoint publishes a `click_events` message and returns
  the `302` immediately — it does not wait for the message to be
  processed, just for the broker to accept it (and even that failure is
  swallowed, not surfaced to the visitor; see `EventPublisher`).
- A separate worker pool consumes at its own pace, persists to Postgres
  (raw event + daily rollup upsert + denormalized counter bump), and can
  fall behind during a traffic spike without the redirect path even
  noticing.
- **Durability**: persistent messages + durable queue mean an in-flight
  click event survives a broker restart, unlike an in-memory queue.
- **Retry + DLQ**: processing failures (e.g., a transient DB hiccup)
  retry with exponential backoff up to a bounded number of attempts, then
  dead-letter to `click_events.dlq` instead of looping forever or
  silently dropping data — see the Architecture Dashboard's DLQ counter.

**Why not just a background `asyncio.create_task()` in the API process?**
That would lose the click event entirely if the API process crashed
before the task ran, wouldn't survive past a single process, and
couples worker concurrency to API replica count instead of letting them
scale independently. **Why not Kafka?** Kafka is the right call at a
much higher event-volume / multi-consumer-group scale (e.g., the same
click stream feeding analytics *and* fraud detection *and* a
recommendation pipeline). For a single logical consumer group writing to
one database, RabbitMQ's operational simplicity (and built-in DLQ
support) is the better fit — this is itself a tradeoff worth saying out
loud in an interview, not a default.

---

## Caching strategy

**Pattern: cache-aside (lazy loading) on read, explicit invalidation on
write**, with a write-through populate on create:

- **Read**: check Redis → on hit, done. On miss, read Postgres and
  populate Redis before returning.
- **Create**: populate Redis immediately so the very first redirect for
  a brand-new link is a cache hit, not a guaranteed miss.
- **Update/Delete**: invalidate (delete) the cache key rather than trying
  to patch it in place — simpler, and avoids subtle staleness bugs where
  an in-place update race leaves half-applied state in the cache.

**Why not write-through for every write?** Most URL fields (target URL,
title) change rarely after creation relative to how often they're read,
so paying a cache-write cost on every create/update is acceptable, but
optimizing further (e.g., write-through on every analytics counter bump)
would add complexity for no real benefit — click counts are read from
Postgres aggregates (`url_daily_stats`), not from the per-URL cache
entry, so they don't need to invalidate the redirect cache at all.

**TTL**: 1 hour, sliding (reset on every read via `SETEX`). This bounds
staleness if a URL is deactivated and the cache invalidation step
somehow doesn't fire (e.g., a deploy mid-request), without requiring
every single read to check Postgres.

---

## Scaling strategy

| Layer | Strategy | Why |
|---|---|---|
| API | Horizontal — stateless replicas behind a load balancer | JWT auth = no server-side session; any replica serves any request |
| Worker | Horizontal — competing consumers on one queue | No coordination needed; RabbitMQ distributes messages |
| Redis | Vertical (single instance) for this project; Redis Cluster is the real next step | Cache misses degrade gracefully to Postgres — Redis being down doesn't take the system down, just slows it |
| RabbitMQ | Single instance for this project; mirrored/quorum queues across a cluster is the real next step | Durability already handled per-instance; HA is the natural follow-up |
| PostgreSQL | Single primary; **read replicas documented as the next step** (see below) | Writes are infrequent (URL creates, click event upserts); reads (dashboard, analytics) are the part that grows with traffic |

### PostgreSQL read replicas (documented, not implemented)

Analytics queries (`/api/v1/analytics/*`) and the dashboard's list/search
endpoint are read-heavy and tolerate eventual consistency — a dashboard
showing click counts that are a few hundred milliseconds stale is
completely fine. These are exactly the queries you'd route to a read
replica pool once query volume on the primary starts contending with
write throughput (URL creates, the worker's click upserts).

The implementation path with the stack already in place: SQLAlchemy's
`async_sessionmaker` supports binding different engines per session: a
`get_db_write()` dependency for the primary (used by mutating endpoints
and the worker), and `get_db_read()` for a replica-pool engine (used by
`/analytics/*` and `GET /urls`). This wasn't built in this project
because doing so without a real second Postgres instance to validate
against would just be unused code — it's documented here as the
identified next step rather than implemented speculatively.

---

## Tradeoffs made (explicitly, on purpose)

| Decision | What we gained | What we gave up |
|---|---|---|
| Base62(sequence id) short codes instead of random+retry | No collisions ever, no retry loop, shorter codes sooner | Codes are sequential/guessable — a production system handling sensitive links would add a permutation step (e.g. Feistel cipher over the ID space) to de-correlate code from creation order |
| Denormalized `urls.total_clicks` counter | O(1) "top URLs" sort without scanning `click_events` | Eventually consistent — there's a small window between a click event being published and the counter reflecting it |
| Mocked geo IP lookup (static hash → country) | No external GeoIP service dependency, fully reproducible in a sandboxed/offline environment | Not real geographic data — explicitly labeled as mocked everywhere it surfaces (API docs, dashboard) |
| Manual retry/backoff in the worker instead of a delayed-exchange plugin | No extra RabbitMQ plugin dependency; behavior is visible in plain Python | Backoff sleep is in-process per message, not a true distributed delay — fine at this scale, would need the plugin (or a dedicated delay queue) at high message volume |
| Single Postgres instance, no read replicas | Simpler to run and reason about for a portfolio project | Doesn't yet demonstrate the read-scaling story beyond documentation — see above |
| `init-db/init.sql` instead of Alembic migrations | One less moving part for a from-scratch `docker compose up` | No migration history / rollback story for schema changes — noted as a hardening checklist item |
| Rate limiting counts failed requests (e.g. a `409` conflict) against the same quota as successful ones | Simpler single check at the top of the handler | A user retrying a bad request burns part of their quota — a more lenient design would only count successful creates |

---

## What this project is *not* trying to be

It's not trying to handle billions of URLs, multi-region active-active
writes, or real fraud detection on click streams. It's trying to be the
smallest system that still makes every one of the decisions above real
and runnable, so each one can be discussed from "here's the code" rather
than "here's the theory."
