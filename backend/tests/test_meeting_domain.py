import uuid
import pytest
import datetime
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from app.core.database import Base, get_db
from app.core.clock import Clock
from app.core.idempotency import IdempotencyMiddleware
from app.core.jwks import jwks_manager
from app.main import app
from app.models.meeting import (
    Meeting, MeetingLifecycle, MeetingWorkflow, Participant,
    Recording, RecordingUploadStatus, OutboxEvent, WorkflowStage, WorkflowStatus
)
from app.models.auth import User, Workspace, Membership
from app.infrastructure.storage import MinIOStorageService
from app.infrastructure.events import (
    OutboxDispatcherService, RedisEventDispatcher, enqueue_outbox_event
)

# Setup isolated testing SQLite DB
TEST_DATABASE_URL = "sqlite:///./test_meeting_domain.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Mock Clock Provider
class FrozenClock:
    def __init__(self, time_val: datetime.datetime):
        self.time_val = time_val

    def now(self) -> datetime.datetime:
        return self.time_val

@pytest.fixture(name="db_session")
def fixture_db_session():
    """Provisions and teardowns an isolated test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Reset Clock provider
    Clock.set_provider(None)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def fixture_client(db_session):
    """Overrides the database dependency and provides a test client instance."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

# ==========================================
# 1. DOMAIN AGGREGATE INVARIANT TESTS
# ==========================================

def test_meeting_start_recording_invariants(db_session):
    """Asserts meeting start state changes and validation bounds."""
    now = datetime.datetime(2026, 7, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
    Clock.set_provider(FrozenClock(now))

    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        title="Engineering Design Review",
        created_by=user_id,
        scheduled_start=now,
        lifecycle_state=MeetingLifecycle.Scheduled
    )
    db_session.add(meeting)
    db_session.commit()

    # 1. Start meeting
    meeting.start_recording(user_id)
    assert meeting.lifecycle_state == MeetingLifecycle.Recording
    assert meeting.actual_start == now
    assert len(meeting.domain_events) == 1
    assert meeting.domain_events[0]["event_type"] == "MeetingStarted"

    # 2. Cannot restart or start if ended
    meeting.lifecycle_state = MeetingLifecycle.Ended
    with pytest.raises(ValueError, match="Cannot start a meeting in state .*Ended"):
        meeting.start_recording(user_id)

    # 3. Cannot start soft-deleted meeting
    meeting.lifecycle_state = MeetingLifecycle.Scheduled
    meeting.deleted_at = now
    with pytest.raises(ValueError, match="Cannot start a soft-deleted meeting"):
        meeting.start_recording(user_id)


def test_meeting_end_meeting_invariants(db_session):
    """Asserts meeting end validation checks."""
    now = datetime.datetime(2026, 7, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
    Clock.set_provider(FrozenClock(now))

    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        title="Engineering Design Review",
        created_by=user_id,
        scheduled_start=now,
        actual_start=now,
        lifecycle_state=MeetingLifecycle.Recording
    )
    db_session.add(meeting)
    db_session.commit()

    # 1. End meeting
    meeting.end_meeting()
    assert meeting.lifecycle_state == MeetingLifecycle.Ended
    assert meeting.actual_end == now

    # 2. End time before start validation
    meeting.lifecycle_state = MeetingLifecycle.Recording
    meeting.actual_start = now + datetime.timedelta(minutes=10)
    with pytest.raises(ValueError, match="Meeting cannot end before it has started"):
        meeting.end_meeting()


def test_meeting_archive_workflow_checks(db_session):
    """Asserts archiving is blocked if AI processing workflows are running."""
    now = datetime.datetime(2026, 7, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    
    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        title="Design Session",
        created_by=user_id,
        scheduled_start=now,
        lifecycle_state=MeetingLifecycle.Ended
    )
    # Add a pending workflow
    wf = MeetingWorkflow(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        stage=WorkflowStage.Transcription,
        status=WorkflowStatus.Running
    )
    meeting.workflows.append(wf)
    db_session.add(meeting)
    db_session.commit()

    # 1. Should raise ValueError since Transcription is Running
    with pytest.raises(ValueError, match="Cannot archive meeting while workflow stage Transcription is Running"):
        meeting.archive_meeting()

    # 2. Archive succeeds if all completed
    wf.status = WorkflowStatus.Completed
    db_session.commit()
    meeting.archive_meeting()
    assert meeting.lifecycle_state == MeetingLifecycle.Archived


def test_recording_immutability(db_session):
    """Asserts recording details cannot be updated once verified."""
    meeting_id = uuid.uuid4()
    recording = Recording(
        id=uuid.uuid4(),
        meeting_id=meeting_id,
        s3_bucket="noted-maam-audio-chunks",
        s3_key="audio.wav",
        original_filename="audio.wav",
        checksum="",
        file_size=1024,
        duration_ms=0,
        bitrate=0,
        codec="",
        sample_rate=0,
        channels=0,
        upload_status=RecordingUploadStatus.Uploading
    )
    db_session.add(recording)
    db_session.commit()

    # 1. First verification succeeds
    recording.verify("sha_hash_1", 1000, 128000, "mp3", 16000, 1)
    assert recording.upload_status == RecordingUploadStatus.Verified
    assert recording.checksum == "sha_hash_1"

    # 2. Second verification fails
    with pytest.raises(ValueError, match="Cannot modify properties of an already verified recording"):
        recording.verify("sha_hash_2", 2000, 256000, "wav", 44100, 2)


# ==========================================
# 2. CONCURRENCY & TRANSACTION WORKFLOW TESTS
# ==========================================

def test_optimistic_locking_conflict(db_session):
    """Asserts version checks block concurrent updates."""
    now = datetime.datetime(2026, 7, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        title="Weekly Sync",
        created_by=user_id,
        scheduled_start=now,
        lifecycle_state=MeetingLifecycle.Waiting,
        version=1
    )
    db_session.add(meeting)
    db_session.commit()

    # Fetch two instances representing separate concurrent requests
    session1 = TestingSessionLocal()
    session2 = TestingSessionLocal()

    m1 = session1.query(Meeting).filter(Meeting.id == meeting.id).first()
    m2 = session2.query(Meeting).filter(Meeting.id == meeting.id).first()

    # Session 1 updates state
    m1.lifecycle_state = MeetingLifecycle.Recording
    session1.commit()

    # Session 2 attempts update with stale version mapping
    m2.lifecycle_state = MeetingLifecycle.Ended
    with pytest.raises(StaleDataError):
        session2.commit()

    session1.close()
    session2.close()


def test_outbox_transaction_rollback(db_session):
    """Verifies that outbox events are not committed if a transaction fails."""
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    
    # Start transaction scope
    db_session.begin_nested() # use nested savepoint

    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        title="Outbox Integrity Test",
        created_by=user_id,
        scheduled_start=Clock.now(),
        lifecycle_state=MeetingLifecycle.Waiting
    )
    db_session.add(meeting)

    enqueue_outbox_event(
        db_session=db_session,
        aggregate_id=meeting.id,
        aggregate_type="Meeting",
        event_type="MeetingCreated",
        event_version=1,
        payload={"title": meeting.title},
        metadata_block={"correlation_id": "test"}
    )

    # Force rollback
    db_session.rollback()

    # Verify no events or meetings are committed
    saved_meetings = db_session.query(Meeting).filter(Meeting.title == "Outbox Integrity Test").all()
    saved_events = db_session.query(OutboxEvent).filter(OutboxEvent.aggregate_id == meeting.id).all()
    
    assert len(saved_meetings) == 0
    assert len(saved_events) == 0


# ==========================================
# 3. LEASED DISPATCHER WORKER TESTS
# ==========================================

@pytest.mark.asyncio
async def test_outbox_dispatcher_leased_locking():
    """Verifies leasing locks and status mutations on dispatcher processing."""
    # Setup database local memory
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()

    event_id = uuid.uuid4()
    outbox = OutboxEvent(
        id=event_id,
        event_uuid=uuid.uuid4(),
        aggregate_id=uuid.uuid4(),
        aggregate_type="Meeting",
        event_type="MeetingCreated",
        event_version=1,
        payload={"key": "val"},
        metadata_block={"trace_id": "123"},
        status="PENDING",
        occurred_at=datetime.datetime.now(datetime.timezone.utc)
    )
    session.add(outbox)
    session.commit()

    # Mock dispatcher interface
    mock_dispatcher = MagicMock(spec=RedisEventDispatcher)
    mock_dispatcher.dispatch = AsyncMock()

    service = OutboxDispatcherService(session_factory, mock_dispatcher)
    processed = await service.process_batch(batch_size=10)

    assert processed == 1
    mock_dispatcher.dispatch.assert_called_once()

    # Check database event status is updated to DELIVERED
    session.expire_all()
    db_event = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
    assert db_event.status == "DELIVERED"
    assert db_event.published_at is not None

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_outbox_dispatcher_offline_failover_and_dead_letter():
    """Verifies offline retry locks and transition limits to DEAD_LETTER status."""
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()

    event_id = uuid.uuid4()
    outbox = OutboxEvent(
        id=event_id,
        event_uuid=uuid.uuid4(),
        aggregate_id=uuid.uuid4(),
        aggregate_type="Meeting",
        event_type="MeetingCreated",
        event_version=1,
        payload={"key": "val"},
        metadata_block={"trace_id": "123"},
        status="PENDING",
        retry_count=0,
        occurred_at=datetime.datetime.now(datetime.timezone.utc)
    )
    session.add(outbox)
    session.commit()

    # Mock dispatcher to throw connection errors (simulating Redis outage)
    mock_dispatcher = MagicMock(spec=RedisEventDispatcher)
    mock_dispatcher.dispatch = AsyncMock(side_effect=ConnectionError("Redis connection lost"))

    service = OutboxDispatcherService(session_factory, mock_dispatcher)

    # 1. First failure
    await service.process_batch()
    session.expire_all()
    db_event = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
    assert db_event.status == "PENDING"
    assert db_event.retry_count == 1

    # 2. Force retry counts to 4 and trigger again
    db_event.retry_count = 4
    session.commit()

    await service.process_batch()
    session.expire_all()
    db_event = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
    
    # Should move to DEAD_LETTER after 5th failure
    assert db_event.status == "DEAD_LETTER"

    session.close()
    Base.metadata.drop_all(bind=engine)


# ==========================================
# 4. API CONTROLLER GATEWAY TESTS
# ==========================================

def test_api_upload_validation_gates(client, db_session):
    """Asserts magic bytes content sniffing validation constraints on uploads."""
    # Setup test workspace and user contexts
    user = User(id=uuid.uuid4(), email="uploader@example.com", password_hash="hash", is_active=True)
    workspace = Workspace(id=uuid.uuid4(), name="Test Workspace")
    membership = Membership(user_id=user.id, workspace_id=workspace.id, role="Owner")
    db_session.add_all([user, workspace, membership])
    db_session.commit()

    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title="Upload Test Meeting",
        created_by=user.id,
        scheduled_start=Clock.now(),
        lifecycle_state=MeetingLifecycle.Recording
    )
    db_session.add(meeting)
    db_session.commit()

    # Generate a valid signed token for uploader account context
    access_token_payload = {
        "iss": "auth.notedmaam.ai",
        "sub": str(user.id),
        "aud": "api.notedmaam.ai",
        "exp": int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)).timestamp()),
        "nbf": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
        "iat": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
        "jti": uuid.uuid4().hex,
        "workspace_id": str(workspace.id),
    }
    active_key = jwks_manager.get_active_key()
    access_token = active_key.sign_token(access_token_payload)

    # Authenticate headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Workspace-ID": str(workspace.id)
    }
    # 1. Invalid Magic Bytes: Upload a standard text file
    response = client.post(
        f"/api/v1/meeting/{meeting.id}/upload",
        files={"file": ("test.wav", b"INVALID_HEADER_BYTES", "audio/wav")},
        headers=headers
    )
    assert response.status_code == 400
    assert "signature validation failure" in response.json()["detail"]

    # 2. Valid Magic Bytes: Upload file starting with RIFF
    with patch.object(MinIOStorageService, "upload_file_stream", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = {
            "checksum": "mocked_sha256",
            "file_size": 24,
            "s3_key": "mock_key",
            "s3_bucket": "mock_bucket"
        }

        response = client.post(
            f"/api/v1/meeting/{meeting.id}/upload",
            files={"file": ("test.wav", b"RIFFchunkofbyteshere", "audio/wav")},
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["checksum"] == "mocked_sha256"


# ==========================================
# 5. IDEMPOTENCY KEY CACHING TESTS
# ==========================================

def test_api_idempotency_caching(client, db_session):
    """Verifies that duplicate requests receive cached responses and prevent concurrent processing."""
    # Setup test workspace and user contexts
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()

    user = User(id=user_id, email="idempotence@example.com", password_hash="hash", is_active=True)
    workspace = Workspace(id=workspace_id, name="Idempotency Org")
    membership = Membership(user_id=user_id, workspace_id=workspace_id, role="Member")
    db_session.add_all([user, workspace, membership])
    db_session.commit()

    # Generate a valid signed token
    access_token_payload = {
        "iss": "auth.notedmaam.ai",
        "sub": str(user_id),
        "aud": "api.notedmaam.ai",
        "exp": int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)).timestamp()),
        "nbf": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
        "iat": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
        "jti": uuid.uuid4().hex,
        "workspace_id": str(workspace_id),
    }
    active_key = jwks_manager.get_active_key()
    access_token = active_key.sign_token(access_token_payload)

    # Mock route handler to increment execution counters
    execution_counter = 0

    @app.post("/api/v1/meetings/idempotency_test")
    def handler(request: Request):
        nonlocal execution_counter
        execution_counter += 1
        return {"execution_number": execution_counter}

    class MockRedis:
        def __init__(self):
            self.store = {}
        async def get(self, key):
            return self.store.get(key)
        async def set(self, key, value, ex=None):
            self.store[key] = value
            return True

    mock_redis = MockRedis()
    IdempotencyMiddleware._mock_redis = mock_redis

    try:
        # Setup headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Idempotency-Key": "unique_key_123",
            "X-Workspace-ID": str(workspace_id)
        }

        # Request 1: Executed first time
        response1 = client.post("/api/v1/meetings/idempotency_test", headers=headers)
        assert response1.status_code == 200
        assert response1.json()["execution_number"] == 1

        # Request 2: Replayed with identical Idempotency-Key
        response2 = client.post("/api/v1/meetings/idempotency_test", headers=headers)
        assert response2.status_code == 200
        # Should yield cached response details with execution count remaining at 1
        assert response2.json()["execution_number"] == 1
        assert execution_counter == 1
    finally:
        IdempotencyMiddleware._mock_redis = None
