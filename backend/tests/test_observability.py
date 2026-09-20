"""
Test Suite — Platform Operations & Observability Bounded Context

Verifies:
  1. ContextVars trace ID isolation (concurrency validation).
  2. HTTP Middleware trace header extraction and injection.
  3. Outbox trace propagation.
  4. /metrics endpoint serialization compliance.
  5. /health/ready connectivity check states.
"""
import uuid
import asyncio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.clock import Clock
from app.core.tracing import TraceContextManager, TracingMiddleware
from app.core.metrics import metrics_collector
from app.models.meeting import OutboxEvent
from app.infrastructure.events import enqueue_outbox_event
from app.main import app

TEST_OBSERVABILITY_DB = "sqlite:///./test_observability.db"
engine = create_engine(TEST_OBSERVABILITY_DB, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db_session")
def fixture_db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


# ============================================================
# 1. Tracing Context Isolation Tests
# ============================================================

@pytest.mark.asyncio
async def test_tracing_context_isolation_concurrency():
    """Asserts that tracing ContextVars maintain isolation and do not leak under concurrency."""
    async def run_context_task(task_id: str, delay: float):
        TraceContextManager.set_trace_context(task_id, f"span-{task_id}")
        await asyncio.sleep(delay)
        val = TraceContextManager.get_trace_id()
        span = TraceContextManager.get_span_id()
        TraceContextManager.clear_trace_context()
        return val, span

    results = await asyncio.gather(
        run_context_task("trace-1", 0.05),
        run_context_task("trace-2", 0.01),
        run_context_task("trace-3", 0.03),
    )

    assert results[0] == ("trace-1", "span-trace-1")
    assert results[1] == ("trace-2", "span-trace-2")
    assert results[2] == ("trace-3", "span-trace-3")


# ============================================================
# 2. HTTP Trace Headers Injection Tests
# ============================================================

def test_tracing_middleware_header_propagation():
    """Verifies that TracingMiddleware captures X-Trace-ID request headers and maps them to responses."""
    client = TestClient(app)
    trace_id = str(uuid.uuid4())
    
    response = client.get("/", headers={"X-Trace-ID": trace_id})
    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == trace_id
    assert "X-Span-ID" in response.headers


# ============================================================
# 3. Outbox Tracing Integration Tests
# ============================================================

def test_outbox_telemetry_propagation(db_session):
    """Verifies enqueue_outbox_event automatically captures active trace IDs into metadata_block."""
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    TraceContextManager.set_trace_context(trace_id, span_id)

    try:
        meeting_id = uuid.uuid4()
        enqueue_outbox_event(
            db_session=db_session,
            aggregate_id=meeting_id,
            aggregate_type="Meeting",
            event_type="TestEvent",
            event_version=1,
            payload={"msg": "hello"},
            metadata_block={}
        )
        db_session.commit()

        event = db_session.query(OutboxEvent).filter(OutboxEvent.aggregate_id == meeting_id).first()
        assert event is not None
        assert event.metadata_block["trace_id"] == trace_id
        assert event.metadata_block["span_id"] == span_id
    finally:
        TraceContextManager.clear_trace_context()


# ============================================================
# 4. Metrics Scraper Serializations Tests
# ============================================================

def test_metrics_compliant_serializer_format():
    """Verifies MetricsCollector exports standard Prometheus scraper string serialization models."""
    metrics_collector.increment("http_requests_total", 1.0, {"endpoint": "/ready"})
    metrics_collector.set_gauge("active_workers", 3.0)
    metrics_collector.record_duration("transcription_duration_ms", 120.0, {"provider": "mock"})

    payload = metrics_collector.export_prometheus_format()
    assert 'http_requests_total{endpoint="/ready"} 1.0' in payload
    assert 'active_workers 3.0' in payload
    assert 'transcription_duration_ms_count{provider="mock"} 1' in payload
    assert 'transcription_duration_ms_sum{provider="mock"} 120.0' in payload


# ============================================================
# 5. Diagnostics Health Endpoints Tests
# ============================================================

def test_liveness_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/health/ready")
    # Should complete successfully when dependencies exist
    assert response.status_code in [200, 503]


def test_readiness_endpoint_unhealthy():
    """Asserts ready check returns 503 Service Unavailable when the database is offline."""
    from app.core.database import get_db
    
    # Override database dependency with failing stub
    def mock_failing_db():
        class MockSession:
            def execute(self, query):
                raise RuntimeError("PostgreSQL Connection Terminated")
        yield MockSession()

    app.dependency_overrides[get_db] = mock_failing_db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()["detail"]
        assert data["status"] == "unready"
        assert "PostgreSQL Connection Terminated" in data["diagnostics"]["database"]
    finally:
        # Clear override
        app.dependency_overrides.clear()


def test_readiness_endpoint_unhealthy_redis_minio(monkeypatch):
    """Asserts ready check returns 503 when Redis or Storage connection raises exceptions."""
    import redis.asyncio as aioredis
    from app.infrastructure.storage import MinIOStorageService

    # Stub redis ping failure
    async def mock_ping(*args, **kwargs):
        raise RuntimeError("Redis Connection Timed Out")

    class MockRedis:
        def __init__(self, *args, **kwargs): pass
        async def ping(self): return await mock_ping()
        async def close(self): pass

    monkeypatch.setattr(aioredis, "from_url", lambda *args, **kwargs: MockRedis())

    # Stub MinIO storage init failure
    def mock_storage_init(*args, **kwargs):
        raise RuntimeError("MinIO Connection Offline")

    monkeypatch.setattr(MinIOStorageService, "__init__", mock_storage_init)

    client = TestClient(app)
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    data = response.json()["detail"]
    assert "Redis Connection Timed Out" in data["diagnostics"]["cache"]
    assert "MinIO Connection Offline" in data["diagnostics"]["storage"]


def test_readiness_endpoint_success(monkeypatch):
    """Asserts ready check returns 200 OK when all backend systems are healthy."""
    import redis.asyncio as aioredis
    from app.infrastructure.storage import MinIOStorageService
    from app.core.database import get_db

    # 1. Mock DB Session execute SELECT 1
    def mock_db_session():
        class MockSession:
            def execute(self, query):
                return None
        yield MockSession()

    app.dependency_overrides[get_db] = mock_db_session

    # 2. Mock Redis Ping success
    async def mock_ping():
        return True

    class MockRedis:
        def __init__(self, *args, **kwargs): pass
        async def ping(self): return await mock_ping()
        async def close(self): pass

    monkeypatch.setattr(aioredis, "from_url", lambda *args, **kwargs: MockRedis())

    # 3. Mock MinIO storage init success
    monkeypatch.setattr(MinIOStorageService, "__init__", lambda *args, **kwargs: None)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["diagnostics"]["database"] == "healthy"
        assert data["diagnostics"]["cache"] == "healthy"
        assert data["diagnostics"]["storage"] == "healthy"
    finally:
        app.dependency_overrides.clear()



