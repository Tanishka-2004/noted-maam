import uuid
import logging
import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import webrtcvad
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import redis.asyncio as aioredis
from app.core.config import settings
from app.core.clock import Clock
from app.models.meeting import Meeting, MeetingLifecycle, Recording, RecordingUploadStatus
from app.infrastructure.storage import ObjectStorageService, MinIOStorageService
from app.infrastructure.events import enqueue_outbox_event

logger = logging.getLogger(__name__)

class MediaSessionState(str, Enum):
    Active = "Active"
    Completed = "Completed"
    Failed = "Failed"

class MediaSession:
    def __init__(
        self,
        session_id: uuid.UUID,
        meeting_id: uuid.UUID,
        participant_id: uuid.UUID,
        state: MediaSessionState = MediaSessionState.Active,
        expected_sequence: int = 1,
        bytes_received: int = 0,
        cumulative_hash: str = "",
        codec: str = "audio/wav",
        created_at: Optional[datetime] = None,
        last_activity: Optional[datetime] = None,
    ):
        self.session_id = session_id
        self.meeting_id = meeting_id
        self.participant_id = participant_id
        self.state = state
        self.expected_sequence = expected_sequence
        self.bytes_received = bytes_received
        self.cumulative_hash = cumulative_hash
        self.codec = codec
        self.created_at = created_at or Clock.now()
        self.last_activity = last_activity or Clock.now()

    def to_dict(self) -> Dict[str, str]:
        return {
            "session_id": str(self.session_id),
            "meeting_id": str(self.meeting_id),
            "participant_id": str(self.participant_id),
            "state": self.state.value,
            "expected_sequence": str(self.expected_sequence),
            "bytes_received": str(self.bytes_received),
            "cumulative_hash": self.cumulative_hash,
            "codec": self.codec,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "MediaSession":
        return cls(
            session_id=uuid.UUID(data["session_id"]),
            meeting_id=uuid.UUID(data["meeting_id"]),
            participant_id=uuid.UUID(data["participant_id"]),
            state=MediaSessionState(data["state"]),
            expected_sequence=int(data["expected_sequence"]),
            bytes_received=int(data["bytes_received"]),
            cumulative_hash=data.get("cumulative_hash", ""),
            codec=data.get("codec", "audio/wav"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
        )


def analyze_voice_activity(data: bytes, sample_rate: int = 16000, aggressiveness: int = 2) -> Dict[str, Any]:
    """Slices 16-bit mono PCM bytes into 30ms frames and returns speech stats."""
    # Ensure sample rate is valid for webrtcvad
    if sample_rate not in (8000, 16000, 32000, 48000):
        return {"speech_ratio": 1.0, "is_speech_present": True}

    vad = webrtcvad.Vad(aggressiveness)
    
    frame_size_ms = 30
    bytes_per_sample = 2
    samples_per_frame = int(sample_rate * (frame_size_ms / 1000.0))
    frame_bytes_len = samples_per_frame * bytes_per_sample
    
    speech_frames = 0
    total_frames = 0
    
    for i in range(0, len(data) - frame_bytes_len + 1, frame_bytes_len):
        frame = data[i : i + frame_bytes_len]
        total_frames += 1
        try:
            if vad.is_speech(frame, sample_rate):
                speech_frames += 1
        except Exception:
            pass
            
    speech_ratio = (speech_frames / total_frames) if total_frames > 0 else 0.0
    return {
        "speech_ratio": speech_ratio,
        "speech_duration_ms": speech_frames * frame_size_ms,
        "total_duration_ms": total_frames * frame_size_ms,
        "is_speech_present": speech_ratio > 0.05
    }


class MediaIngestionService:
    # Set mock_redis dynamically in tests
    _mock_redis = None

    def __init__(self, storage: Optional[ObjectStorageService] = None):
        self.storage = storage or MinIOStorageService()
        self._redis_client = None

    @property
    def redis_client(self):
        if self._mock_redis is not None:
            return self._mock_redis
        if self.__class__._mock_redis is not None:
            return self.__class__._mock_redis
        if self._redis_client is None:
            self._redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis_client

    def _get_redis_key(self, session_id: uuid.UUID) -> str:
        return f"media:session:{session_id}"

    def _get_chunk_hash_key(self, session_id: uuid.UUID, sequence_number: int) -> str:
        return f"media:session:{session_id}:chunk:{sequence_number}:hash"

    async def initialize_session(
        self,
        meeting_id: uuid.UUID,
        participant_id: uuid.UUID,
        codec: str,
        db_session: Session
    ) -> MediaSession:
        """Schedules media context inside Redis if the parent meeting state is active."""
        # Query meeting to check exists and active state
        meeting = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")

        if meeting.lifecycle_state != MeetingLifecycle.Recording:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Incompatible meeting lifecycle: {meeting.lifecycle_state}. Ingestion is allowed only in 'Recording' state."
            )

        session_id = uuid.uuid4()
        session = MediaSession(
            session_id=session_id,
            meeting_id=meeting_id,
            participant_id=participant_id,
            codec=codec
        )

        redis_key = self._get_redis_key(session_id)
        await self.redis_client.hset(redis_key, mapping=session.to_dict())
        # Set 15-minute TTL on the active upload context
        await self.redis_client.expire(redis_key, 900)

        return session

    async def get_session(self, session_id: uuid.UUID) -> Optional[MediaSession]:
        """Resolves active MediaSession parameters from Redis cache."""
        redis_key = self._get_redis_key(session_id)
        data = await self.redis_client.hgetall(redis_key)
        if not data:
            return None
        return MediaSession.from_dict(data)

    async def process_chunk(
        self,
        session_id: uuid.UUID,
        sequence_number: int,
        data: bytes,
        checksum: str,
        is_final: bool,
        db_session: Session
    ) -> Dict[str, Any]:
        """Validates sequence order and integrity hash, processes voice frames, and saves chunk objects."""
        session = await self.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found or expired.")

        if session.state != MediaSessionState.Active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Session is in invalid state: {session.state}")

        # 1. Check for duplicate sequence numbers (idempotent retries)
        if sequence_number < session.expected_sequence:
            # Look up previous chunk's cached checksum hash
            hash_key = self._get_chunk_hash_key(session_id, sequence_number)
            cached_checksum = await self.redis_client.get(hash_key)
            if cached_checksum == checksum:
                logger.info(f"Idempotent chunk replay detected. Sequence: {sequence_number}")
                return {
                    "session_id": str(session_id),
                    "expected_sequence": session.expected_sequence,
                    "bytes_received": session.bytes_received,
                    "state": session.state.value,
                    "idempotent_replay": True
                }
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate sequence number with conflicting payload.")

        # 2. Check for missing sequence numbers (gaps)
        if sequence_number > session.expected_sequence:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Out of order sequence detected. Expected: {session.expected_sequence}, received: {sequence_number}."
            )

        # 3. Verify SHA-256 integrity hash
        sha256 = hashlib.sha256(data).hexdigest()
        if sha256 != checksum:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chunk integrity verification failed (SHA-256 mismatch).")

        # 4. Run Voice Activity Detection
        vad_data = data
        if sequence_number == 1 and data.startswith(b"RIFF"):
            # Skip 44-byte WAV header for VAD alignment check
            vad_data = data[44:]
        vad_res = analyze_voice_activity(vad_data)

        # 5. Write to object storage temporary folder
        # Query workspace ID from the meeting model to build path prefix
        meeting = db_session.query(Meeting).filter(Meeting.id == session.meeting_id).first()
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")

        temp_key = f"workspaces/{meeting.workspace_id}/meetings/{meeting.id}/temp_session_{session_id}/chunk_{sequence_number:06d}.bin"
        await self.storage.write_chunk(settings.MINIO_BUCKET_NAME, temp_key, data)

        # 6. Update MediaSession state in Redis cache
        session.bytes_received += len(data)
        session.expected_sequence = sequence_number + 1
        session.last_activity = Clock.now()

        redis_key = self._get_redis_key(session_id)
        await self.redis_client.hset(redis_key, mapping=session.to_dict())
        await self.redis_client.expire(redis_key, 900)

        # Store sequence checksum hash for idempotency checks
        hash_key = self._get_chunk_hash_key(session_id, sequence_number)
        await self.redis_client.set(hash_key, checksum, ex=900)

        # 7. Finalization on EOF
        if is_final:
            session.state = MediaSessionState.Completed
            await self.redis_client.hset(redis_key, mapping=session.to_dict())

            # Perform sequential S3 chunks merge
            source_prefix = f"workspaces/{meeting.workspace_id}/meetings/{meeting.id}/temp_session_{session_id}/"
            recording_id = uuid.uuid4()
            final_key = f"workspaces/{meeting.workspace_id}/meetings/{meeting.id}/final_recording_{recording_id}.wav"

            try:
                merge_res = await self.storage.merge_session_chunks(
                    bucket=settings.MINIO_BUCKET_NAME,
                    source_prefix=source_prefix,
                    destination_key=final_key,
                    expected_count=sequence_number
                )
            except Exception as err:
                session.state = MediaSessionState.Failed
                await self.redis_client.hset(redis_key, mapping=session.to_dict())
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Audio chunks consolidation failure: {err}"
                )

            # Estimate duration based on byte scale of standard WAV format
            duration_s = merge_res["file_size"] / 32000.0  # 16kHz * 2 bytes/sample mono = 32000 bytes/s

            # Write Recording entity in database
            duration_ms = int(duration_s * 1000)
            recording = Recording(
                id=recording_id,
                meeting_id=meeting.id,
                file_size=merge_res["file_size"],
                checksum=merge_res["checksum"],
                s3_bucket=merge_res["s3_bucket"],
                s3_key=merge_res["s3_key"],
                upload_status=RecordingUploadStatus.Verified,
                duration_ms=duration_ms,
                original_filename="recording.wav",
                codec=session.codec or "audio/wav",
                sample_rate=16000,
                channels=1,
                bitrate=256000
            )
            db_session.add(recording)

            # Register RecordingVerified event in transaction outbox
            enqueue_outbox_event(
                db_session=db_session,
                aggregate_id=meeting.id,
                aggregate_type="Meeting",
                event_type="RecordingVerified",
                event_version=1,
                payload={
                    "meeting_id": str(meeting.id),
                    "recording_id": str(recording_id),
                    "checksum": recording.checksum,
                    "file_size": recording.file_size,
                    "duration_seconds": duration_s
                },
                metadata_block={
                    "tenant_id": str(meeting.workspace_id),
                    "participant_id": str(session.participant_id)
                }
            )

            # Flush outbox event & recording commit transaction
            db_session.commit()

            # Purge Redis session cache
            await self.redis_client.delete(redis_key)
            for s in range(1, sequence_number + 1):
                await self.redis_client.delete(self._get_chunk_hash_key(session_id, s))

            return {
                "session_id": str(session_id),
                "recording_id": str(recording_id),
                "state": "Completed",
                "bytes_received": session.bytes_received,
                "checksum": recording.checksum,
                "file_size": recording.file_size,
                "duration_seconds": duration_s
            }

        return {
            "session_id": str(session_id),
            "expected_sequence": session.expected_sequence,
            "bytes_received": session.bytes_received,
            "state": session.state.value
        }
