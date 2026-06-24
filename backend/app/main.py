from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.v1 import analytics, auth, health, redirect, urls
from app.core.config import settings
from app.core.gauge_sync import gauge_sync_loop
from app.core.logging import configure_logging
from app.core.middleware import PrometheusMiddleware, RequestContextMiddleware
from app.core.rabbitmq import declare_topology, get_connection
from app.db.redis_client import redis_client
from app.services.event_publisher import event_publisher

configure_logging()
logger = structlog.get_logger("main")


def _setup_otel(app: FastAPI) -> None:
    if not settings.OTEL_ENABLED:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource(attributes={SERVICE_NAME: settings.OTEL_SERVICE_NAME})
        provider = TracerProvider(resource=resource)
        if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
            exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument()
        RedisInstrumentor().instrument()
        logger.info("otel_instrumentation_enabled")
    except Exception:
        logger.exception("otel_setup_failed_continuing_without_tracing")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup_begin", env=settings.ENV)

    # Declare RabbitMQ topology once at startup (idempotent) and start the
    # long-lived publisher connection used by the redirect hot path.
    connection = await get_connection()
    channel = await connection.channel()
    await declare_topology(channel)
    await connection.close()
    await event_publisher.start()

    import asyncio
    _gauge_task = asyncio.create_task(gauge_sync_loop())

    logger.info("startup_complete")
    yield

    logger.info("shutdown_begin")
    _gauge_task.cancel()
    await event_publisher.stop()
    await redis_client.aclose()
    logger.info("shutdown_complete")


app = FastAPI(
    title=settings.APP_NAME,
    description="A production-grade URL shortening platform demonstrating "
    "cache-aside reads, event-driven analytics, and horizontally scalable "
    "service design.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RequestContextMiddleware)

_setup_otel(app)


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Prometheus scrape endpoint — exposes all CacheFlow metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    logger.warning("validation_error", errors=jsonable_encoder(exc.errors()))
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


# Routers under /api/v1
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(urls.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(health.router, prefix=settings.API_V1_PREFIX)

# Redirect router mounted at root so short links are clean: GET /{code}
app.include_router(redirect.router)
