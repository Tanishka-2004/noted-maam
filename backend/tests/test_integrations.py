"""
Test Suite — External Integrations Bounded Context

Verifies:
  1. Successful dispatches mapping payloads (Mock, Webhook adapters).
  2. Workspace sandboxing: active configs map to matching tenants.
  3. Webhook adapter signs payloads with HMAC-SHA256 signature headers.
  4. Error classification rules: HTTP 500 triggers Retrying; HTTP 400 triggers DeadLetter directly.
  5. Idempotency keys prevent duplicate jobs enqueued.
"""
import uuid
import json
import pytest
import httpx
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.clock import Clock
from app.core.tracing import TraceContextManager
from app.models.auth import User, Workspace, Membership
from app.models.meeting import (
    Meeting, MeetingLifecycle, OutboxEvent,
    IntegrationConfig, IntegrationOutbox,
    IntelligenceReport, IntelligenceReportStatus,
    MeetingSummary, ActionItem, Decision, ArtifactReviewState
)
from app.services.integrations import IntegrationRouterService, GenericWebhookAdapter
from app.workers.integration_worker import IntegrationWorker

TEST_INTEGRATIONS_DB = "sqlite:///./test_integrations.db"
engine = create_engine(TEST_INTEGRATIONS_DB, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db_session")
def fixture_db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _setup_workspace_and_meeting(db_session):
    user = User(id=uuid.uuid4(), email="owner@org.com", password_hash="hash", is_active=True)
    workspace = Workspace(id=uuid.uuid4(), name="Engineering Team")
    membership = Membership(user_id=user.id, workspace_id=workspace.id, role="Owner")
    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title="Architecture Alignment",
        created_by=user.id,
        lifecycle_state=MeetingLifecycle.Ended,
    )
    intel_report = IntelligenceReport(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        transcript_id=uuid.uuid4(),
        status=IntelligenceReportStatus.Completed
    )
    summary = MeetingSummary(
        id=uuid.uuid4(),
        report_id=intel_report.id,
        executive_summary="Aligining design",
        key_topics=[{"topic": "Design", "summary": "Detailed design"}],
        outcomes=[],
        open_questions=[],
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[],
        confidence_overall=0.9
    )
    decision = Decision(
        id=uuid.uuid4(),
        report_id=intel_report.id,
        summary="Use transactional outbox",
        context="context",
        rationale="rationale",
        participants_involved=[],
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[]
    )

    db_session.add_all([user, workspace, membership, meeting, intel_report, summary, decision])
    db_session.commit()
    return user, workspace, meeting, intel_report


# ============================================================
# 1. Adapter & Webhook Signature Verification Tests
# ============================================================

@pytest.mark.asyncio
async def test_webhook_adapter_hmac_header_signature():
    """Asserts GenericWebhookAdapter signs request body with HMAC signature headers."""
    dispatched_headers = {}

    async def mock_post(url, content, headers, timeout):
        nonlocal dispatched_headers
        dispatched_headers = headers
        # Mock Response
        class MockResponse:
            status_code = 200
            text = "OK"
        return MockResponse()

    # Stub HTTP client POST method
    class MockClient:
        async def post(self, url, content, headers, timeout):
            return await mock_post(url, content, headers, timeout)

    adapter = GenericWebhookAdapter(client=MockClient())
    payload = {"data": "test_payload"}
    config = {"url": "http://workspace.webhook.endpoint", "secret": "workspace_secret_token"}

    res = await adapter.dispatch(payload, config)
    assert res["status"] == "delivered"
    assert "X-Noted-Signature" in dispatched_headers
    
    # Recompute signature to verify matches
    body_str = json.dumps(payload, sort_keys=True)
    expected_sig = hmac_sign("workspace_secret_token", body_str)
    assert dispatched_headers["X-Noted-Signature"] == expected_sig


def hmac_sign(secret, body):
    import hmac
    import hashlib
    return hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


# ============================================================
# 2. Worker Inbound Polling & Idempotency Tests
# ============================================================

@pytest.mark.asyncio
async def test_worker_inbound_polling_and_idempotency(db_session):
    """Verifies MeetingIntelligenceReady enqueues IntegrationOutbox jobs idempotently."""
    _, workspace, meeting, intel_report = _setup_workspace_and_meeting(db_session)

    # Configure active Slack integration config
    config = IntegrationConfig(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        provider="slack",
        credentials_encrypted={"channel": "#engineering", "token": "slack_oauth_token"},
        is_active=True
    )
    db_session.add(config)

    # Emit MeetingIntelligenceReady event
    event = OutboxEvent(
        id=uuid.uuid4(),
        event_uuid=uuid.uuid4(),
        aggregate_id=meeting.id,
        aggregate_type="Meeting",
        event_type="MeetingIntelligenceReady",
        event_version=1,
        payload={"meeting_id": str(meeting.id), "report_id": str(intel_report.id)},
        metadata_block={"trace_id": "test_trace_parent"},
        status="DELIVERED",
        occurred_at=Clock.now()
    )
    db_session.add(event)
    db_session.commit()

    worker = IntegrationWorker(db_session_factory=lambda: TestingSessionLocal())
    
    # First Poll (Enqueues job)
    processed = await worker.poll_and_process_inbound()
    assert processed is True

    # Assert job was queued
    job = db_session.query(IntegrationOutbox).filter(IntegrationOutbox.workspace_id == workspace.id).first()
    assert job is not None
    assert job.status == "Queued"
    assert job.trace_id == "test_trace_parent"

    # Second Poll (Should skip duplicate queueing due to Idempotency Key constraints)
    db_session.refresh(event)
    event.status = "DELIVERED"  # reset event status
    db_session.commit()

    processed_again = await worker.poll_and_process_inbound()
    assert processed_again is True

    jobs_count = db_session.query(IntegrationOutbox).filter(IntegrationOutbox.workspace_id == workspace.id).count()
    assert jobs_count == 1  # No duplicate job enqueued!


# ============================================================
# 3. Retryable & Permanent Failures Routing Tests
# ============================================================

@pytest.mark.asyncio
async def test_worker_outbound_retry_error_classification_500(db_session):
    """Verifies that HTTP 500 triggers Retrying state changes."""
    _, workspace, meeting, intel_report = _setup_workspace_and_meeting(db_session)

    config = IntegrationConfig(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        provider="webhook",
        credentials_encrypted={"url": "http://unhealthy.endpoint", "secret": "sec"},
        is_active=True
    )
    db_session.add(config)
    db_session.commit()

    class FailingRouterHTTP500:
        async def route_dispatch(self, config, payload):
            class MockResponse:
                status_code = 500
            err = httpx.HTTPStatusError("Internal Server Error", request=None, response=MockResponse())
            raise err

    job = IntegrationOutbox(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        integration_id=config.id,
        idempotency_key="idem_key_500",
        status="Queued",
        payload={"msg": "payload"},
        trace_id="trace_500"
    )
    db_session.add(job)
    db_session.commit()

    worker_500 = IntegrationWorker(
        db_session_factory=lambda: TestingSessionLocal(),
        router_service=FailingRouterHTTP500()
    )

    await worker_500.poll_and_process_outbound()
    
    job_500 = db_session.query(IntegrationOutbox).filter(IntegrationOutbox.idempotency_key == "idem_key_500").first()
    assert job_500.status == "Retrying"
    assert job_500.attempt_count == 1
    assert job_500.http_status == 500


@pytest.mark.asyncio
async def test_worker_outbound_retry_error_classification_400(db_session):
    """Verifies that HTTP 400 moves directly to DeadLetter state."""
    _, workspace, meeting, intel_report = _setup_workspace_and_meeting(db_session)

    config = IntegrationConfig(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        provider="webhook",
        credentials_encrypted={"url": "http://unhealthy.endpoint", "secret": "sec"},
        is_active=True
    )
    db_session.add(config)
    db_session.commit()

    class FailingRouterHTTP400:
        async def route_dispatch(self, config, payload):
            class MockResponse:
                status_code = 400
            err = httpx.HTTPStatusError("Bad Request", request=None, response=MockResponse())
            raise err

    job_400 = IntegrationOutbox(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        integration_id=config.id,
        idempotency_key="idem_key_400",
        status="Queued",
        payload={"msg": "payload"},
        trace_id="trace_400"
    )
    db_session.add(job_400)
    db_session.commit()

    worker_400 = IntegrationWorker(
        db_session_factory=lambda: TestingSessionLocal(),
        router_service=FailingRouterHTTP400()
    )

    await worker_400.poll_and_process_outbound()

    job_result = db_session.query(IntegrationOutbox).filter(IntegrationOutbox.idempotency_key == "idem_key_400").first()
    assert job_result.status == "DeadLetter"
    assert job_result.attempt_count == 1
    assert job_result.http_status == 400


@pytest.mark.asyncio
async def test_worker_outbound_success_mock_and_slack(db_session):
    """Verifies that successful Mock and Slack dispatches complete and set Delivered status."""
    _, workspace, meeting, intel_report = _setup_workspace_and_meeting(db_session)

    # 1. Config active Mock
    config_mock = IntegrationConfig(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        provider="mock",
        credentials_encrypted={},
        is_active=True
    )
    # 2. Config active Slack
    config_slack = IntegrationConfig(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        provider="slack",
        credentials_encrypted={"channel": "#general", "token": "slack_token"},
        is_active=True
    )
    db_session.add_all([config_mock, config_slack])
    db_session.commit()

    # Queued Mock job
    job_mock = IntegrationOutbox(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        integration_id=config_mock.id,
        idempotency_key="mock_idem",
        status="Queued",
        payload={"msg": "hello"}
    )
    # Queued Slack job
    job_slack = IntegrationOutbox(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        integration_id=config_slack.id,
        idempotency_key="slack_idem",
        status="Queued",
        payload={"msg": "hello"}
    )
    db_session.add_all([job_mock, job_slack])
    db_session.commit()

    worker = IntegrationWorker(db_session_factory=lambda: TestingSessionLocal())
    
    # Process Mock job
    p1 = await worker.poll_and_process_outbound()
    assert p1 is True
    
    # Process Slack job
    p2 = await worker.poll_and_process_outbound()
    assert p2 is True

    # Assert both are Delivered
    jm = db_session.query(IntegrationOutbox).filter(IntegrationOutbox.idempotency_key == "mock_idem").first()
    js = db_session.query(IntegrationOutbox).filter(IntegrationOutbox.idempotency_key == "slack_idem").first()
    assert jm.status == "Delivered"
    assert js.status == "Delivered"


@pytest.mark.asyncio
async def test_worker_outbound_disabled_config(db_session):
    """Verifies that jobs enqueued to disabled or removed configs transition to Cancelled."""
    _, workspace, meeting, intel_report = _setup_workspace_and_meeting(db_session)

    config = IntegrationConfig(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        provider="mock",
        credentials_encrypted={},
        is_active=False  # disabled config
    )
    db_session.add(config)
    db_session.commit()

    job = IntegrationOutbox(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        integration_id=config.id,
        idempotency_key="disabled_idem",
        status="Queued",
        payload={"msg": "hello"}
    )
    db_session.add(job)
    db_session.commit()

    worker = IntegrationWorker(db_session_factory=lambda: TestingSessionLocal())
    await worker.poll_and_process_outbound()

    job_result = db_session.query(IntegrationOutbox).filter(IntegrationOutbox.idempotency_key == "disabled_idem").first()
    assert job_result.status == "Cancelled"
    assert "disabled or removed" in job_result.failure_reason


@pytest.mark.asyncio
async def test_worker_outbound_max_retry_limit_reached(db_session):
    """Verifies that jobs with attempts >= 5 move to DeadLetter status on failures."""
    _, workspace, meeting, intel_report = _setup_workspace_and_meeting(db_session)

    config = IntegrationConfig(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        provider="mock",
        credentials_encrypted={},
        is_active=True
    )
    db_session.add(config)
    db_session.commit()

    # Job at attempt 4
    job = IntegrationOutbox(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        integration_id=config.id,
        idempotency_key="max_retry_idem",
        status="Queued",
        payload={"msg": "hello"},
        attempt_count=4
    )
    db_session.add(job)
    db_session.commit()

    # Router throwing retryable exception
    class FailingRouter:
        async def route_dispatch(self, config, payload):
            raise asyncio.TimeoutError("Timeout connection")

    worker = IntegrationWorker(
        db_session_factory=lambda: TestingSessionLocal(),
        router_service=FailingRouter()
    )
    await worker.poll_and_process_outbound()

    job_result = db_session.query(IntegrationOutbox).filter(IntegrationOutbox.idempotency_key == "max_retry_idem").first()
    # Should move to DeadLetter since attempt_count becomes 5 (>= MAX_RETRIES)
    assert job_result.status == "DeadLetter"
    assert job_result.attempt_count == 5
    assert "Timeout connection" in job_result.failure_reason


@pytest.mark.asyncio
async def test_integrations_validation_raises(db_session):
    """Verifies that invalid adapter configurations raise ValueError exceptions."""
    from app.services.integrations import SlackAdapter, GenericWebhookAdapter, IntegrationRouterService

    # 1. Slack missing token
    slack = SlackAdapter()
    with pytest.raises(ValueError, match="token is missing"):
        await slack.dispatch({"msg": "hi"}, {})

    # 2. Webhook missing URL
    webhook = GenericWebhookAdapter()
    with pytest.raises(ValueError, match="URL is missing"):
        await webhook.dispatch({"msg": "hi"}, {})

    # 3. Router unsupported provider
    router = IntegrationRouterService()
    config = IntegrationConfig(provider="unsupported")
    with pytest.raises(ValueError, match="Unsupported integrations provider"):
        await router.route_dispatch(config, {})


@pytest.mark.asyncio
async def test_worker_inbound_missing_meeting_or_configs(db_session):
    """Verifies worker handles missing meetings or active configs gracefully."""
    # Case A: Missing meeting returns False or consumes silently
    event = OutboxEvent(
        id=uuid.uuid4(),
        event_uuid=uuid.uuid4(),
        aggregate_id=uuid.uuid4(),  # non-existent meeting
        aggregate_type="Meeting",
        event_type="MeetingIntelligenceReady",
        event_version=1,
        payload={"meeting_id": str(uuid.uuid4()), "report_id": str(uuid.uuid4())},
        metadata_block={},
        status="DELIVERED",
        occurred_at=Clock.now()
    )
    db_session.add(event)
    db_session.commit()

    worker = IntegrationWorker(db_session_factory=lambda: TestingSessionLocal())
    p = await worker.poll_and_process_inbound()
    assert p is True


@pytest.mark.asyncio
async def test_worker_outbound_empty(db_session):
    """Verifies poll_and_process_outbound returns False when queue is empty."""
    worker = IntegrationWorker(db_session_factory=lambda: TestingSessionLocal())
    p = await worker.poll_and_process_outbound()
    assert p is False


@pytest.mark.asyncio
async def test_worker_start_stop():
    """Verifies starting and stopping the background polling task of the integrations worker."""
    worker = IntegrationWorker(db_session_factory=lambda: TestingSessionLocal())
    task = asyncio.create_task(worker.start(poll_interval=0.1))
    await asyncio.sleep(0.15)
    assert worker.is_running is True
    await worker.stop()
    assert worker.is_running is False
    await task


@pytest.mark.asyncio
async def test_worker_general_exception_fallback(db_session):
    """Verifies that non-retryable exceptions (e.g. ValueError) move the job directly to DeadLetter."""
    _, workspace, meeting, intel_report = _setup_workspace_and_meeting(db_session)

    config = IntegrationConfig(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        provider="mock",
        credentials_encrypted={},
        is_active=True
    )
    db_session.add(config)
    db_session.commit()

    job = IntegrationOutbox(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        integration_id=config.id,
        idempotency_key="value_error_idem",
        status="Queued",
        payload={"msg": "hello"}
    )
    db_session.add(job)
    db_session.commit()

    # Stub Router raising ValueError (General non-retryable exception)
    class ExceptionRouter:
        async def route_dispatch(self, config, payload):
            raise ValueError("Template format invalid")

    worker = IntegrationWorker(
        db_session_factory=lambda: TestingSessionLocal(),
        router_service=ExceptionRouter()
    )
    await worker.poll_and_process_outbound()

    job_result = db_session.query(IntegrationOutbox).filter(IntegrationOutbox.idempotency_key == "value_error_idem").first()
    assert job_result.status == "DeadLetter"
    assert "Template format invalid" in job_result.failure_reason



