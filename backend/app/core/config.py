"""
Centralized application configuration.

Everything is sourced from environment variables (with sane local-dev
defaults) so the same image runs unmodified across dev/staging/prod —
only the .env / environment differs. This is what lets the API tier be
stateless and horizontally scalable: no config is baked into the build.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "CacheFlow"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Security / JWT ---
    SECRET_KEY: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7d

    # --- CORS ---
    # NOTE: kept as a plain str (not List[str]) on purpose. pydantic-settings
    # attempts to JSON-decode env values for complex/list-typed fields at the
    # *source* level, before any field_validator runs — so a plain
    # comma-separated env value like "http://a,http://b" raises a
    # SettingsError before we ever get a chance to split it. A str field +
    # computed property sidesteps that entirely.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # --- Database ---
    POSTGRES_USER: str = "cacheflow"
    POSTGRES_PASSWORD: str = "cacheflow"
    POSTGRES_DB: str = "cacheflow"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_REPLICA_HOST: str = "postgres_replica"
    POSTGRES_PORT: int = 5432
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_REPLICA_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_REPLICA_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Used by Alembic, which doesn't speak asyncpg."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Redis ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL_OVERRIDE: str | None = None
    URL_CACHE_TTL_SECONDS: int = 3600

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_URL_OVERRIDE:
            return self.REDIS_URL_OVERRIDE
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- Rate limiting ---
    RATE_LIMIT_CREATE_MAX: int = 30
    RATE_LIMIT_CREATE_WINDOW_SECONDS: int = 60
    RATE_LIMIT_REDIRECT_MAX: int = 100
    RATE_LIMIT_REDIRECT_WINDOW_SECONDS: int = 60

    # --- RabbitMQ ---
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_MANAGEMENT_PORT: int = 15672
    RABBITMQ_USER: str = "cacheflow"
    RABBITMQ_PASSWORD: str = "cacheflow"
    RABBITMQ_VHOST: str = "/"
    CLICK_EVENTS_EXCHANGE: str = "click_events"
    CLICK_EVENTS_QUEUE: str = "click_events.process"
    CLICK_EVENTS_DLX: str = "click_events.dlx"
    CLICK_EVENTS_DLQ: str = "click_events.dlq"
    CLICK_EVENT_MAX_RETRIES: int = 3

    @property
    def RABBITMQ_URL(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
        )

    # --- Frontend / short URL base ---
    SHORT_URL_BASE: str = "http://localhost:8000"

    # --- Observability ---
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "cacheflow-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # --- Worker ---
    WORKER_PREFETCH_COUNT: int = 10
    WORKER_HEARTBEAT_INTERVAL_SECONDS: int = 5
    WORKER_HEARTBEAT_TTL_SECONDS: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
