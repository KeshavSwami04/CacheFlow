-- CacheFlow schema bootstrap.
-- Mirrors backend/app/models/*.py exactly. Mounted into
-- /docker-entrypoint-initdb.d/ so Postgres runs it once on first boot of a
-- fresh data volume. For an evolving production schema, replace this with
-- Alembic migrations (the SQLAlchemy models are already migration-ready).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TABLE IF NOT EXISTS urls (
    id              BIGSERIAL PRIMARY KEY,
    short_code      VARCHAR(16) UNIQUE,
    custom_alias    VARCHAR(64) UNIQUE,
    target_url      TEXT NOT NULL,
    title           VARCHAR(255),
    owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    total_clicks    BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_urls_short_code ON urls (short_code);
CREATE INDEX IF NOT EXISTS ix_urls_custom_alias ON urls (custom_alias);
CREATE INDEX IF NOT EXISTS ix_urls_owner_id ON urls (owner_id);
CREATE INDEX IF NOT EXISTS ix_urls_owner_created ON urls (owner_id, created_at);
-- Partial index: only URLs that actually have an expiry are worth
-- indexing for the (not-yet-implemented) expiry-sweep background job —
-- keeps the index small relative to total row count.
CREATE INDEX IF NOT EXISTS ix_urls_expires_at_active ON urls (expires_at) WHERE expires_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS click_events (
    id            BIGSERIAL PRIMARY KEY,
    url_id        BIGINT NOT NULL REFERENCES urls(id) ON DELETE CASCADE,
    clicked_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    referrer      VARCHAR(512),
    country_code  VARCHAR(2),
    device_type   VARCHAR(32),
    ip_hash       VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS ix_click_events_clicked_at ON click_events (clicked_at);
CREATE INDEX IF NOT EXISTS ix_click_events_url_clicked ON click_events (url_id, clicked_at);

CREATE TABLE IF NOT EXISTS url_daily_stats (
    url_id              BIGINT NOT NULL REFERENCES urls(id) ON DELETE CASCADE,
    stat_date           DATE NOT NULL,
    click_count         INTEGER NOT NULL DEFAULT 0,
    referrer_breakdown  JSONB NOT NULL DEFAULT '{}'::jsonb,
    country_breakdown   JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (url_id, stat_date)
);
