import uuid
import hashlib
import datetime
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.jwks import jwks_manager
from app.main import app
from app.models.auth import User, Workspace, Membership
from app.models.meeting import Meeting, MeetingLifecycle, Recording, RecordingUploadStatus
from app.services.media import MediaIngestionService, MediaSessionState, MediaSession
from app.api.meeting import media_service
from app.infrastructure.storage import MinIOStorageService

# Setup isolated testing SQLite DB
TEST_DATABASE_URL = "sqlite:///./test_media.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def fixture_db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def fixture_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


class MockRedis:
    def __init__(self):
        self.store = {}

    async def hset(self, key, mapping=None, **kwargs):
        if key not in self.store:
            self.store[key] = {}
        if mapping:
            self.store[key].update(mapping)
        if kwargs:
            self.store[key].update(kwargs)
        return True

    async def hgetall(self, key):
        return self.store.get(key, {})

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    async def delete(self, key):
        if key in self.store:
            del self.store[key]
            return 1
        return 0

    async def expire(self, key, time):
        return True


class MockStorageService:
    def __init__(self):
        self.chunks = {}

    async def write_chunk(self, bucket: str, key: str, data: bytes) -> None:
        self.chunks[key] = data

    async def merge_session_chunks(self, bucket: str, source_prefix: str, destination_key: str, expected_count: int) -> dict:
        keys = [k for k in self.chunks.keys() if k.startswith(source_prefix)]
        
        def extract_seq(key: str) -> int:
            try:
                filename = key.split("/")[-1]
                seq_part = filename.replace("chunk_", "").replace(".bin", "")
                return int(seq_part)
            except Exception:
                return 999999
        keys.sort(key=extract_seq)

        if len(keys) != expected_count:
            raise ValueError(f"Chunk count mismatch. Expected {expected_count}, found {len(keys)}")

        merged_data = bytearray()
        for key in keys:
            merged_data.extend(self.chunks[key])

        checksum = hashlib.sha256(merged_data).hexdigest()
        
        # Clean up chunks
        for key in keys:
            del self.chunks[key]

        self.chunks[destination_key] = bytes(merged_data)

        return {
            "checksum": checksum,
            "file_size": len(merged_data),
            "s3_key": destination_key,
            "s3_bucket": bucket
        }


# ==========================================
# MEDIA STREAMING & INGESTION TESTS
# ==========================================

def test_session_initialization_state_gates(client, db_session):
    """Verifies that media session requests are rejected unless the meeting is actively recording."""
    user = User(id=uuid.uuid4(), email="session@example.com", password_hash="hash", is_active=True)
    workspace = Workspace(id=uuid.uuid4(), name="Streaming Org")
    membership = Membership(user_id=user.id, workspace_id=workspace.id, role="Owner")
    db_session.add_all([user, workspace, membership])
    db_session.commit()

    # 1. Test against Scheduled meeting (Should fail with 400)
    meeting_scheduled = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title="Scheduled Room",
        created_by=user.id,
        lifecycle_state=MeetingLifecycle.Scheduled
    )
    db_session.add(meeting_scheduled)
    db_session.commit()

    access_token_payload = {
        "iss": "auth.notedmaam.ai",
        "sub": str(user.id),
        "aud": "api.notedmaam.ai",
        "workspace_id": str(workspace.id),
    }
    active_key = jwks_manager.get_active_key()
    access_token = active_key.sign_token(access_token_payload)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Workspace-ID": str(workspace.id)
    }

    response = client.post(
        f"/api/v1/meeting/{meeting_scheduled.id}/media/session",
        json={"codec": "audio/wav"},
        headers=headers
    )
    assert response.status_code == 400
    assert "Incompatible meeting lifecycle" in response.json()["detail"]

    # 2. Test against actively Recording meeting (Should succeed with 201)
    meeting_recording = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title="Active Recording Room",
        created_by=user.id,
        lifecycle_state=MeetingLifecycle.Recording
    )
    db_session.add(meeting_recording)
    db_session.commit()

    mock_redis = MockRedis()
    media_service._mock_redis = mock_redis
    try:
        response_ok = client.post(
            f"/api/v1/meeting/{meeting_recording.id}/media/session",
            json={"codec": "audio/wav"},
            headers=headers
        )
        assert response_ok.status_code == 201
        res_data = response_ok.json()
        assert res_data["state"] == "Active"
        assert uuid.UUID(res_data["session_id"])
    finally:
        media_service._mock_redis = None


def test_chunk_upload_sequence_and_idempotency(client, db_session):
    """Verifies duplicate chunk idempotency, missing chunk conflicts, and checksum integrity."""
    user = User(id=uuid.uuid4(), email="chunk@example.com", password_hash="hash", is_active=True)
    workspace = Workspace(id=uuid.uuid4(), name="Chunk Org")
    membership = Membership(user_id=user.id, workspace_id=workspace.id, role="Owner")
    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title="Live Ingestion Room",
        created_by=user.id,
        lifecycle_state=MeetingLifecycle.Recording
    )
    db_session.add_all([user, workspace, membership, meeting])
    db_session.commit()

    access_token_payload = {
        "iss": "auth.notedmaam.ai",
        "sub": str(user.id),
        "aud": "api.notedmaam.ai",
        "workspace_id": str(workspace.id),
    }
    active_key = jwks_manager.get_active_key()
    access_token = active_key.sign_token(access_token_payload)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Workspace-ID": str(workspace.id),
        "Content-Type": "application/octet-stream"
    }

    mock_redis = MockRedis()
    mock_storage = MockStorageService()
    
    media_service._mock_redis = mock_redis
    media_service.storage = mock_storage

    try:
        # Create session
        session = MediaSession(
            session_id=uuid.uuid4(),
            meeting_id=meeting.id,
            participant_id=user.id
        )
        redis_key = f"media:session:{session.session_id}"
        asyncio.run(mock_redis.hset(redis_key, mapping=session.to_dict()))

        # Raw mono 16kHz PCM audio samples (960 bytes for a 30ms alignment window)
        pcm_speech = b"\x00\x05" * 480
        checksum_speech = hashlib.sha256(pcm_speech).hexdigest()

        # 1. Upload Chunk 1: Success
        resp1 = client.post(
            f"/api/v1/meeting/{meeting.id}/media/session/{session.session_id}/chunks?sequence_number=1&checksum={checksum_speech}",
            content=pcm_speech,
            headers=headers
        )
        assert resp1.status_code == 200
        assert resp1.json()["expected_sequence"] == 2

        # 2. Upload Chunk 1 Duplicate: Idempotent Success
        resp_dup = client.post(
            f"/api/v1/meeting/{meeting.id}/media/session/{session.session_id}/chunks?sequence_number=1&checksum={checksum_speech}",
            content=pcm_speech,
            headers=headers
        )
        assert resp_dup.status_code == 200
        assert resp_dup.json()["idempotent_replay"] is True

        # 3. Upload Chunk 1 with conflicting checksum: 400 Bad Request
        resp_conf = client.post(
            f"/api/v1/meeting/{meeting.id}/media/session/{session.session_id}/chunks?sequence_number=1&checksum=badchecksum",
            content=pcm_speech,
            headers=headers
        )
        assert resp_conf.status_code == 400

        # 4. Integrity check: upload sequence 2 with wrong checksum: 400 Bad Request
        resp_int = client.post(
            f"/api/v1/meeting/{meeting.id}/media/session/{session.session_id}/chunks?sequence_number=2&checksum=invalidchecksum",
            content=pcm_speech,
            headers=headers
        )
        assert resp_int.status_code == 400

        # 5. Out of order check: upload sequence 3 instead of 2: 409 Conflict
        resp_gap = client.post(
            f"/api/v1/meeting/{meeting.id}/media/session/{session.session_id}/chunks?sequence_number=3&checksum={checksum_speech}",
            content=pcm_speech,
            headers=headers
        )
        assert resp_gap.status_code == 409
        assert "expected: 2" in resp_gap.json()["detail"].lower()

    finally:
        media_service._mock_redis = None
        media_service.storage = MinIOStorageService()


def test_chunk_finalization_and_verification_flow(client, db_session):
    """Verifies sequence completion, chunk merge concatenation, and RecordingVerified outbox log emission."""
    user = User(id=uuid.uuid4(), email="final@example.com", password_hash="hash", is_active=True)
    workspace = Workspace(id=uuid.uuid4(), name="Final Org")
    membership = Membership(user_id=user.id, workspace_id=workspace.id, role="Owner")
    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title="Finalizing Ingestion Room",
        created_by=user.id,
        lifecycle_state=MeetingLifecycle.Recording
    )
    db_session.add_all([user, workspace, membership, meeting])
    db_session.commit()

    access_token_payload = {
        "iss": "auth.notedmaam.ai",
        "sub": str(user.id),
        "aud": "api.notedmaam.ai",
        "workspace_id": str(workspace.id),
    }
    active_key = jwks_manager.get_active_key()
    access_token = active_key.sign_token(access_token_payload)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Workspace-ID": str(workspace.id),
        "Content-Type": "application/octet-stream"
    }

    mock_redis = MockRedis()
    mock_storage = MockStorageService()
    
    media_service._mock_redis = mock_redis
    media_service.storage = mock_storage

    try:
        # Create session
        session = MediaSession(
            session_id=uuid.uuid4(),
            meeting_id=meeting.id,
            participant_id=user.id
        )
        redis_key = f"media:session:{session.session_id}"
        asyncio.run(mock_redis.hset(redis_key, mapping=session.to_dict()))

        pcm_data_1 = b"\x00\x05" * 480
        checksum_1 = hashlib.sha256(pcm_data_1).hexdigest()

        pcm_data_2 = b"\x00\x02" * 480
        checksum_2 = hashlib.sha256(pcm_data_2).hexdigest()

        # Upload Part 1
        resp1 = client.post(
            f"/api/v1/meeting/{meeting.id}/media/session/{session.session_id}/chunks?sequence_number=1&checksum={checksum_1}",
            content=pcm_data_1,
            headers=headers
        )
        assert resp1.status_code == 200

        # Upload Part 2 with is_final=True
        resp2 = client.post(
            f"/api/v1/meeting/{meeting.id}/media/session/{session.session_id}/chunks?sequence_number=2&checksum={checksum_2}&is_final=true",
            content=pcm_data_2,
            headers=headers
        )
        assert resp2.status_code == 200
        res_payload = resp2.json()
        assert res_payload["state"] == "Completed"
        assert res_payload["bytes_received"] == 1920
        assert uuid.UUID(res_payload["recording_id"])

        # Verify SQL DB contains verified recording
        rec_id = uuid.UUID(res_payload["recording_id"])
        recording = db_session.query(Recording).filter(Recording.id == rec_id).first()
        assert recording is not None
        assert recording.upload_status == RecordingUploadStatus.Verified
        assert recording.file_size == 1920

        # Verify Transactional Outbox contains the RecordingVerified event
        from app.models.meeting import OutboxEvent
        outbox_entry = db_session.query(OutboxEvent).filter(
            OutboxEvent.aggregate_id == meeting.id,
            OutboxEvent.event_type == "RecordingVerified"
        ).first()
        assert outbox_entry is not None
        assert outbox_entry.status == "PENDING"
        assert outbox_entry.payload["recording_id"] == str(rec_id)
        assert outbox_entry.payload["file_size"] == 1920

        # Verify Session metadata was cleaned up from Redis
        assert not asyncio.run(mock_redis.hgetall(redis_key))

    finally:
        media_service._mock_redis = None
        media_service.storage = MinIOStorageService()


def test_session_status_progress_queries(client, db_session):
    """Verifies that progress API GET retrieves the correct details of active MediaSessions."""
    user = User(id=uuid.uuid4(), email="progress@example.com", password_hash="hash", is_active=True)
    workspace = Workspace(id=uuid.uuid4(), name="Progress Org")
    membership = Membership(user_id=user.id, workspace_id=workspace.id, role="Owner")
    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title="Query Progress Room",
        created_by=user.id,
        lifecycle_state=MeetingLifecycle.Recording
    )
    db_session.add_all([user, workspace, membership, meeting])
    db_session.commit()

    access_token_payload = {
        "iss": "auth.notedmaam.ai",
        "sub": str(user.id),
        "aud": "api.notedmaam.ai",
        "workspace_id": str(workspace.id),
    }
    active_key = jwks_manager.get_active_key()
    access_token = active_key.sign_token(access_token_payload)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Workspace-ID": str(workspace.id)
    }

    mock_redis = MockRedis()
    media_service._mock_redis = mock_redis

    try:
        session = MediaSession(
            session_id=uuid.uuid4(),
            meeting_id=meeting.id,
            participant_id=user.id,
            expected_sequence=15,
            bytes_received=45000
        )
        redis_key = f"media:session:{session.session_id}"
        asyncio.run(mock_redis.hset(redis_key, mapping=session.to_dict()))

        # Execute GET request
        response = client.get(
            f"/api/v1/meeting/{meeting.id}/media/session/{session.session_id}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["expected_sequence"] == 15
        assert data["bytes_received"] == 45000
        assert data["state"] == "Active"

    finally:
        media_service._mock_redis = None
