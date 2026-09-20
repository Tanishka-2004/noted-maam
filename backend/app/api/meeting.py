import uuid
import asyncio
import logging
from typing import Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db
from app.core.iam import PermissionRequirement
from app.core.clock import Clock
from app.core.config import settings
from app.models.meeting import (
    Meeting, MeetingLifecycle, MeetingWorkflow, Participant,
    Recording, RecordingUploadStatus, WorkflowStage, WorkflowStatus
)
from app.infrastructure.storage import MinIOStorageService
from app.infrastructure.events import enqueue_outbox_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meeting", tags=["Meetings"])

# Initialize Storage Service
storage_service = MinIOStorageService()

class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    scheduled_start: Optional[datetime] = None

class MeetingResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    description: Optional[str]
    lifecycle_state: str
    version: int
    created_by: uuid.UUID
    scheduled_start: datetime
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]

    class Config:
        from_attributes = True


@router.post(
    "/start",
    status_code=status.HTTP_201_CREATED,
    response_model=MeetingResponse,
    dependencies=[Depends(PermissionRequirement("meeting.write"))],
)
async def create_meeting(
    data: MeetingCreate, request: Request, db: Session = Depends(get_db)
) -> Any:
    """Schedules/creates a new meeting room context."""
    workspace_id = request.state.workspace_id
    user_id = request.state.user_id
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active workspace context is missing.",
        )

    now = Clock.now()
    sched_start = data.scheduled_start or now
    lifecycle = MeetingLifecycle.Scheduled if sched_start > now else MeetingLifecycle.Waiting

    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        title=data.title,
        description=data.description,
        created_by=user_id,
        scheduled_start=sched_start,
        lifecycle_state=lifecycle,
        version=1,
    )

    # Initialize workflow structures
    for stage in WorkflowStage:
        wf = MeetingWorkflow(
            id=uuid.uuid4(),
            meeting_id=meeting.id,
            stage=stage,
            status=WorkflowStatus.Pending
        )
        meeting.workflows.append(wf)

    # Create host participant record
    host = Participant(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        user_id=user_id,
        display_name="Host User",
        role="Host",
        invitation_status="Accepted",
        is_external=False,
        joined_at=now
    )
    meeting.participants.append(host)

    db.add(meeting)

    # Enqueue Outbox Event
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    metadata_block = {
        "correlation_id": trace_id,
        "causation_id": request_id,
        "trace_id": trace_id,
        "request_id": request_id,
        "tenant_id": str(workspace_id)
    }

    enqueue_outbox_event(
        db_session=db,
        aggregate_id=meeting.id,
        aggregate_type="Meeting",
        event_type="MeetingCreated",
        event_version=1,
        payload={
            "meeting_id": str(meeting.id),
            "workspace_id": str(workspace_id),
            "title": meeting.title,
            "created_by": str(user_id)
        },
        metadata_block=metadata_block
    )

    try:
        db.commit()
        db.refresh(meeting)
        return meeting
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{meeting_id}/start",
    status_code=status.HTTP_200_OK,
    response_model=MeetingResponse,
    dependencies=[Depends(PermissionRequirement("meeting.write"))],
)
async def start_meeting(
    meeting_id: uuid.UUID, request: Request, db: Session = Depends(get_db)
) -> Any:
    """Starts recording of a meeting room."""
    workspace_id = request.state.workspace_id
    user_id = request.state.user_id

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")

    if meeting.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Workspace tenant isolation violation.")

    try:
        # Aggregate mutation
        meeting.start_recording(user_id)

        # Enqueue Outbox event
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        metadata_block = {
            "correlation_id": trace_id,
            "causation_id": request_id,
            "trace_id": trace_id,
            "request_id": request_id,
            "tenant_id": str(workspace_id)
        }

        # Select the pending event added by start_recording mutator
        for event in meeting.domain_events:
            enqueue_outbox_event(
                db_session=db,
                aggregate_id=meeting.id,
                aggregate_type="Meeting",
                event_type=event["event_type"],
                event_version=event["version"],
                payload=event["payload"],
                metadata_block=metadata_block
            )
        # Clear consumed domain events
        meeting.domain_events.clear()

        db.commit()
        db.refresh(meeting)
        return meeting
    except ValueError as val_err:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{meeting_id}/upload",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(PermissionRequirement("meeting.write"))],
)
async def upload_recording(
    meeting_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    duration_ms: int = Query(default=0),
    bitrate: int = Query(default=128000),
    codec: str = Query(default="pcm_s16le"),
    sample_rate: int = Query(default=16000),
    channels: int = Query(default=1),
    language_hint: str = Query(default="en-US"),
    db: Session = Depends(get_db)
) -> Any:
    """Streams audio recording directly to MinIO and validates checksums and magic bytes."""
    workspace_id = request.state.workspace_id

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")

    if meeting.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Workspace tenant isolation violation.")

    # 1. Invariant check: cannot upload unless recording or ended
    if meeting.lifecycle_state not in (MeetingLifecycle.Recording, MeetingLifecycle.Ended):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload rejected. Meeting must be in Recording or Ended lifecycle (current: {meeting.lifecycle_state})"
        )

    # 2. Sniff Magic bytes (Validate WAV file starts with RIFF)
    header = await file.read(4)
    await file.seek(0)
    if header != b"RIFF":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content signature validation failure. Expected a valid RIFF/WAVE audio file."
        )

    # Max size validation: 500MB
    MAX_SIZE = 500 * 1024 * 1024
    # Check headers size if sent, otherwise checked dynamically
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload exceeds maximum limit of 500MB."
        )

    # Initialize a draft Recording entry in DB (Waiting status)
    recording_id = uuid.uuid4()
    s3_key = f"workspaces/{workspace_id}/meetings/{meeting_id}/recordings/{recording_id}.wav"
    bucket = settings.MINIO_BUCKET_NAME

    recording = Recording(
        id=recording_id,
        meeting_id=meeting_id,
        s3_bucket=bucket,
        s3_key=s3_key,
        original_filename=file.filename or "audio.wav",
        checksum="",
        file_size=0,
        duration_ms=0,
        bitrate=0,
        codec=codec,
        sample_rate=sample_rate,
        channels=channels,
        upload_status=RecordingUploadStatus.Uploading,
        language_hint=language_hint,
        storage_provider="minio"
    )
    meeting.recordings.append(recording)
    db.add(recording)
    db.commit()

    # Track trace context variables
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    metadata_block = {
        "correlation_id": trace_id,
        "causation_id": request_id,
        "trace_id": trace_id,
        "request_id": request_id,
        "tenant_id": str(workspace_id)
    }

    # Stream chunks wrapper
    async def chunk_generator():
        chunk_size = 65536
        while True:
            chunk = await asyncio.to_thread(file.file.read, chunk_size)
            if not chunk:
                break
            yield chunk

    # Upload and compute checksum inline in a single pass
    try:
        upload_result = await storage_service.upload_file_stream(
            bucket=bucket,
            key=s3_key,
            file_generator=chunk_generator(),
            content_type=file.content_type or "audio/wav"
        )
        
        # Verify and freeze properties
        recording.verify(
            checksum=upload_result["checksum"],
            duration_ms=duration_ms,
            bitrate=bitrate,
            codec=codec,
            sample_rate=sample_rate,
            channels=channels
        )
        recording.file_size = upload_result["file_size"]
        
        # Update workflows to Queued stage for transcription
        for wf in meeting.workflows:
            if wf.stage == WorkflowStage.Transcription:
                wf.status = WorkflowStatus.Queued

        # Enqueue integration event
        enqueue_outbox_event(
            db_session=db,
            aggregate_id=meeting.id,
            aggregate_type="Meeting",
            event_type="RecordingUploaded",
            event_version=1,
            payload={
                "meeting_id": str(meeting.id),
                "recording_id": str(recording.id),
                "checksum": recording.checksum,
                "s3_key": recording.s3_key,
                "file_size": recording.file_size
            },
            metadata_block=metadata_block
        )

        db.commit()
        return {
            "status": "success",
            "recording_id": recording.id,
            "checksum": recording.checksum,
            "file_size": recording.file_size
        }

    except Exception as upload_err:
        db.rollback()
        # Mark recording as failed
        recording_failed = db.query(Recording).filter(Recording.id == recording_id).first()
        if recording_failed:
            recording_failed.upload_status = RecordingUploadStatus.Failed
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S3 multipart upload failed: {upload_err}"
        )


@router.post(
    "/{meeting_id}/end",
    status_code=status.HTTP_200_OK,
    response_model=MeetingResponse,
    dependencies=[Depends(PermissionRequirement("meeting.write"))],
)
async def end_meeting(
    meeting_id: uuid.UUID, request: Request, db: Session = Depends(get_db)
) -> Any:
    """Ends a running meeting room session."""
    workspace_id = request.state.workspace_id

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")

    if meeting.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Workspace tenant isolation violation.")

    try:
        meeting.end_meeting()

        # Enqueue Outbox Event
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        metadata_block = {
            "correlation_id": trace_id,
            "causation_id": request_id,
            "trace_id": trace_id,
            "request_id": request_id,
            "tenant_id": str(workspace_id)
        }

        for event in meeting.domain_events:
            enqueue_outbox_event(
                db_session=db,
                aggregate_id=meeting.id,
                aggregate_type="Meeting",
                event_type=event["event_type"],
                event_version=event["version"],
                payload=event["payload"],
                metadata_block=metadata_block
            )
        meeting.domain_events.clear()

        db.commit()
        db.refresh(meeting)
        return meeting
    except ValueError as val_err:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/{meeting_id}",
    status_code=status.HTTP_200_OK,
    response_model=MeetingResponse,
    dependencies=[Depends(PermissionRequirement("meeting.read"))],
)
async def get_meeting(
    meeting_id: uuid.UUID, request: Request, db: Session = Depends(get_db)
) -> Any:
    """Retrieves a single meeting record, scoping workspace isolation."""
    workspace_id = request.state.workspace_id

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")

    if meeting.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Workspace tenant isolation violation.")

    return meeting


from app.services.media import MediaIngestionService, MediaSessionState

media_service = MediaIngestionService()

class MediaSessionCreate(BaseModel):
    codec: str = "audio/wav"

class MediaSessionResponse(BaseModel):
    session_id: uuid.UUID
    meeting_id: uuid.UUID
    participant_id: uuid.UUID
    state: str
    expected_sequence: int
    bytes_received: int
    codec: str
    created_at: datetime
    last_activity: datetime

    class Config:
        from_attributes = True

@router.post(
    "/{meeting_id}/media/session",
    status_code=status.HTTP_201_CREATED,
    response_model=MediaSessionResponse,
    dependencies=[Depends(PermissionRequirement("meeting.write"))],
)
async def initialize_media_session(
    meeting_id: uuid.UUID,
    data: MediaSessionCreate,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """Initializes a new media chunk-streaming upload session context."""
    user_id = request.state.user_id
    workspace_id = request.state.workspace_id

    # Verify meeting belongs to user's active tenant workspace (isolation check)
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    if meeting.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Workspace tenant isolation violation."
        )

    session = await media_service.initialize_session(
        meeting_id=meeting_id,
        participant_id=user_id,
        codec=data.codec,
        db_session=db
    )
    return session

@router.post(
    "/{meeting_id}/media/session/{session_id}/chunks",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(PermissionRequirement("meeting.write"))],
)
async def upload_media_chunk(
    meeting_id: uuid.UUID,
    session_id: uuid.UUID,
    request: Request,
    sequence_number: int = Query(..., alias="sequence_number"),
    is_final: bool = Query(False, alias="is_final"),
    checksum: str = Query(..., alias="checksum"),
    db: Session = Depends(get_db)
) -> Any:
    """Ingests a raw PCM audio chunk, validating sequence and integrity hash."""
    user_id = request.state.user_id
    workspace_id = request.state.workspace_id

    # Verify meeting isolation bounds
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    if meeting.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Workspace tenant isolation violation."
        )

    # Read binary raw body
    data = await request.body()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty request payload.")

    res = await media_service.process_chunk(
        session_id=session_id,
        sequence_number=sequence_number,
        data=data,
        checksum=checksum,
        is_final=is_final,
        db_session=db
    )
    return res

@router.get(
    "/{meeting_id}/media/session/{session_id}",
    status_code=status.HTTP_200_OK,
    response_model=MediaSessionResponse,
    dependencies=[Depends(PermissionRequirement("meeting.read"))],
)
async def get_media_session_status(
    meeting_id: uuid.UUID,
    session_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """Retrieves progress and status parameters of an active upload session."""
    workspace_id = request.state.workspace_id

    # Verify meeting isolation
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    if meeting.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Workspace tenant isolation violation."
        )

    session = await media_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found or expired.")
    return session
