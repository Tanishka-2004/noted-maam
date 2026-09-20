import logging
import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import boto3
import redis
from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.auth import router as auth_router
from app.api.meeting import router as meeting_router
from app.core.config import settings
from app.core.database import get_db
from app.core.iam import IAMMiddleware
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.core.idempotency import IdempotencyMiddleware

# Configure structured logging standard output
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("noted-maam")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle managers executing system startups & shutdowns."""
    logger.info("Initializing Noted Ma'am Backend Services...")
    # Validate backing services at boot time
    try:
        # Validate Redis
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        logger.info("Redis cache validation successful.")
    except Exception as e:
        logger.error(f"Redis validation failure at boot: {e}")

    try:
        # Validate S3 Object Store (MinIO)
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ROOT_USER,
            aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
            region_name="us-east-1",
        )
        # Check if bucket exists, create if not
        try:
            s3.head_bucket(Bucket=settings.MINIO_BUCKET_NAME)
        except ClientError:
            s3.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)
            logger.info(
                f"S3 Bucket '{settings.MINIO_BUCKET_NAME}' initialized successfully."
            )
    except Exception as e:
        logger.error(f"S3 Object Store validation failure at boot: {e}")

    # Initialize and start Transactional Outbox event dispatcher worker
    from app.core.database import SessionLocal
    from app.infrastructure.events import OutboxDispatcherService, RedisEventDispatcher

    dispatcher = RedisEventDispatcher()
    dispatcher_service = OutboxDispatcherService(SessionLocal, dispatcher)
    dispatcher_task = asyncio.create_task(dispatcher_service.start(poll_interval=1.0))
    logger.info("Outbox event dispatcher loop started in background.")

    yield
    logger.info("Shutting down Noted Ma'am Backend Services...")
    # Stop background outbox poller loop
    await dispatcher_service.stop()
    await dispatcher_task
    logger.info("Outbox event dispatcher loop terminated.")


from app.core.tracing import TracingMiddleware
from app.core.metrics import metrics_collector
from app.api.health import router as health_router

class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Measures P95 HTTP request duration latencies and increments total count."""
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Track metrics
        endpoint = request.url.path
        labels = {"method": request.method, "endpoint": endpoint, "status": str(response.status_code)}
        metrics_collector.increment("http_requests_total", 1.0, labels)
        metrics_collector.record_duration("http_request_duration_ms", duration_ms, labels)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        return response


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

# Enable CORS for standard UI dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware stack (outermost/first execution is TracingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(IAMMiddleware)
app.add_middleware(RequestMetricsMiddleware)
app.add_middleware(SlidingWindowRateLimiter)
app.add_middleware(TracingMiddleware)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(meeting_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")


@app.get("/metrics")
def get_metrics():
    """Prometheus metrics endpoint exporting standardized stats."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(metrics_collector.export_prometheus_format())


@app.get("/", status_code=status.HTTP_200_OK)
def read_root() -> dict[str, str]:
    """Root info index."""
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "time": str(time.time()),
    }


@app.get("/health", status_code=status.HTTP_200_OK)
def check_health(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Deep healthcheck validating relational database, cache, and object storage."""
    health_status: dict[str, Any] = {
        "status": "healthy",
        "timestamp": str(time.time()),
        "components": {},
    }

    # 1. Test database ping
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database healthcheck failure: {e}")
        health_status["status"] = "degraded"
        health_status["components"]["database"] = f"unhealthy: {e}"

    # 2. Test cache ping
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        health_status["components"]["cache"] = "healthy"
    except Exception as e:
        logger.error(f"Redis cache healthcheck failure: {e}")
        health_status["status"] = "degraded"
        health_status["components"]["cache"] = f"unhealthy: {e}"

    # 3. Test Object Storage
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ROOT_USER,
            aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
        )
        s3.list_buckets()
        health_status["components"]["storage"] = "healthy"
    except Exception as e:
        logger.error(f"Storage healthcheck failure: {e}")
        health_status["status"] = "degraded"
        health_status["components"]["storage"] = f"unhealthy: {e}"

    return health_status
