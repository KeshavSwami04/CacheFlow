"""
All Prometheus metrics for CacheFlow defined in one module.
Imported where needed — counters incremented inline in services,
gauges synced from Redis/RabbitMQ by a background task in main.py.

Metric naming convention: cacheflow_<subsystem>_<name>_<unit>
"""
from prometheus_client import Counter, Gauge, Histogram

# ── HTTP layer (populated by PrometheusMiddleware in middleware.py) ──────────
http_requests_total = Counter(
    "cacheflow_http_requests_total",
    "Total HTTP requests handled",
    ["method", "endpoint", "status_code"],
)
http_request_duration_seconds = Histogram(
    "cacheflow_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── Cache layer ──────────────────────────────────────────────────────────────
cache_hits_total = Counter(
    "cacheflow_cache_hits_total",
    "Redis cache hits on URL resolution",
)
cache_misses_total = Counter(
    "cacheflow_cache_misses_total",
    "Redis cache misses on URL resolution (fell through to Postgres)",
)

# ── Business events ──────────────────────────────────────────────────────────
urls_created_total = Counter(
    "cacheflow_urls_created_total",
    "Short URLs created",
)
redirects_total = Counter(
    "cacheflow_redirects_total",
    "Successful redirects served",
)
rate_limit_rejections_total = Counter(
    "cacheflow_rate_limit_rejections_total",
    "Requests rejected by the sliding-window rate limiter",
    ["endpoint"],
)

# ── System gauges (updated every 15s by background task) ────────────────────
# These bridge the gap between worker-side Redis counters / RabbitMQ stats
# and the Prometheus scrape model: the API reads them from their sources
# and updates these gauges so a single /metrics endpoint covers the whole
# system.
active_workers_gauge = Gauge(
    "cacheflow_active_workers",
    "Number of worker replicas that sent a heartbeat in the last 15s",
)
queue_depth_gauge = Gauge(
    "cacheflow_queue_depth",
    "Current depth of click_events.process queue in RabbitMQ",
)
dlq_depth_gauge = Gauge(
    "cacheflow_dlq_depth",
    "Current depth of the dead-letter queue (failed events)",
)
events_processed_gauge = Gauge(
    "cacheflow_events_processed",
    "Cumulative click events successfully processed by the worker pool",
)
db_pool_checked_out_gauge = Gauge(
    "cacheflow_db_pool_connections_checked_out",
    "SQLAlchemy async pool connections currently in use",
)
db_pool_size_gauge = Gauge(
    "cacheflow_db_pool_size",
    "SQLAlchemy async pool total size (configured max)",
)
