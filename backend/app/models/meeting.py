import uuid
import enum
from datetime import datetime
from typing import Any, Optional, List
from sqlalchemy import (
    String, ForeignKey, DateTime, Integer, Float, Boolean, JSON
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.clock import Clock

class MeetingLifecycle(str, enum.Enum):
    Scheduled = "Scheduled"
    Waiting = "Waiting"
    Recording = "Recording"
    Ended = "Ended"
    Archived = "Archived"

class ProjectStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    UNASSIGNED = "UNASSIGNED"
    Active = "Active"
    Archived = "Archived"

class ConsentStatus(str, enum.Enum):
    UNKNOWN = "UNKNOWN"
    GRANTED = "GRANTED"
    DECLINED = "DECLINED"
    WITHDRAWN = "WITHDRAWN"

class WorkspaceRecordingPolicy(str, enum.Enum):
    STOP = "STOP"
    AUDIO_ONLY = "AUDIO_ONLY"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    COMPLIANCE_RULE = "COMPLIANCE_RULE"

class DecisionState(str, enum.Enum):
    PROPOSED = "PROPOSED"
    DISCUSSED = "DISCUSSED"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVERSED = "REVERSED"

class WorkflowStage(str, enum.Enum):
    Transcription = "Transcription"
    Summarization = "Summarization"
    ActionExtraction = "ActionExtraction"
    ConflictDetection = "ConflictDetection"
    SemanticIndexing = "SemanticIndexing"

class WorkflowStatus(str, enum.Enum):
    Pending = "Pending"
    Queued = "Queued"
    Running = "Running"
    Completed = "Completed"
    Failed = "Failed"
    Partial = "Partial"
    Cancelled = "Cancelled"

class ParticipantRole(str, enum.Enum):
    Host = "Host"
    Speaker = "Speaker"
    Listener = "Listener"

class InvitationStatus(str, enum.Enum):
    Pending = "Pending"
    Accepted = "Accepted"
    Declined = "Declined"

class RecordingUploadStatus(str, enum.Enum):
    Waiting = "Waiting"
    Uploading = "Uploading"
    Uploaded = "Uploaded"
    Verified = "Verified"
    Deleted = "Deleted"

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        String(50), default=ProjectStatus.ASSIGNED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, onupdate=Clock.now, nullable=False
    )

    meetings = relationship("Meeting", back_populates="project")
    tasks = relationship("ActionItem", back_populates="project")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    primary_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True
    )
    lifecycle_state: Mapped[MeetingLifecycle] = mapped_column(
        String(50), default=MeetingLifecycle.Scheduled, nullable=False
    )
    settings: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False)

    __mapper_args__ = {
        "version_id_col": version
    }

    workspace = relationship("Workspace", back_populates="meetings")
    project = relationship("Project", back_populates="meetings", foreign_keys=[primary_project_id])
    participants = relationship(
        "Participant", back_populates="meeting", cascade="all, delete-orphan"
    )
    recordings = relationship(
        "Recording", back_populates="meeting", cascade="all, delete-orphan"
    )
    workflows = relationship(
        "MeetingWorkflow", back_populates="meeting", cascade="all, delete-orphan"
    )
    transcripts = relationship(
        "Transcript", back_populates="meeting", cascade="all, delete-orphan"
    )

    # In-memory list to collect raised domain events during request scope
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._domain_events: List[dict] = []

    @property
    def domain_events(self) -> List[dict]:
        if not hasattr(self, "_domain_events"):
            self._domain_events = []
        return self._domain_events

    def add_domain_event(self, event_type: str, version: int, payload: dict) -> None:
        self.domain_events.append({
            "event_type": event_type,
            "version": version,
            "payload": payload,
            "occurred_at": Clock.now()
        })

    def start_recording(self, user_id: uuid.UUID) -> None:
        """Enforces aggregate transition rules for starting recording."""
        if self.lifecycle_state in (MeetingLifecycle.Ended, MeetingLifecycle.Archived):
            raise ValueError(f"Cannot start a meeting in state {self.lifecycle_state}")
        if self.deleted_at is not None:
            raise ValueError("Cannot start a soft-deleted meeting")
        
        now = Clock.now()
        self.lifecycle_state = MeetingLifecycle.Recording
        if self.actual_start is None:
            self.actual_start = now
        
        self.add_domain_event("MeetingStarted", 1, {
            "meeting_id": str(self.id),
            "workspace_id": str(self.workspace_id),
            "started_by": str(user_id),
            "started_at": now.isoformat()
        })

    def end_meeting(self) -> None:
        """Enforces ending rules."""
        if self.lifecycle_state == MeetingLifecycle.Archived:
            raise ValueError("Cannot end an archived meeting")
        if self.deleted_at is not None:
            raise ValueError("Cannot end a soft-deleted meeting")
        
        now = Clock.now()
        self.lifecycle_state = MeetingLifecycle.Ended
        self.actual_end = now
        
        actual_start_naive = self.actual_start.replace(tzinfo=None) if self.actual_start else None
        actual_end_naive = self.actual_end.replace(tzinfo=None) if self.actual_end else None
        if actual_start_naive and actual_end_naive < actual_start_naive:
            raise ValueError("Meeting cannot end before it has started")

        self.add_domain_event("MeetingEnded", 1, {
            "meeting_id": str(self.id),
            "workspace_id": str(self.workspace_id),
            "ended_at": now.isoformat()
        })

    def archive_meeting(self) -> None:
        """Archives meeting only if all processing pipelines have terminated."""
        if self.lifecycle_state != MeetingLifecycle.Ended:
            raise ValueError("Meeting must be ended before archiving")
        
        # Check active workflows
        for wf in self.workflows:
            if wf.status in (WorkflowStatus.Pending, WorkflowStatus.Queued, WorkflowStatus.Running):
                raise ValueError(f"Cannot archive meeting while workflow stage {wf.stage} is {wf.status}")
        
        self.lifecycle_state = MeetingLifecycle.Archived
        self.add_domain_event("MeetingArchived", 1, {
            "meeting_id": str(self.id),
            "workspace_id": str(self.workspace_id),
            "archived_at": Clock.now().isoformat()
        })

    def soft_delete(self) -> None:
        """Flags soft delete on room lifecycle."""
        if self.lifecycle_state == MeetingLifecycle.Recording:
            raise ValueError("Cannot delete a meeting while it is active and recording")
        
        now = Clock.now()
        self.deleted_at = now
        self.add_domain_event("MeetingDeleted", 1, {
            "meeting_id": str(self.id),
            "workspace_id": str(self.workspace_id),
            "deleted_at": now.isoformat()
        })


class MeetingWorkflow(Base):
    __tablename__ = "meeting_workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False
    )
    stage: Mapped[WorkflowStage] = mapped_column(String(100), nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(String(50), default=WorkflowStatus.Pending, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    meeting = relationship("Meeting", back_populates="workflows")


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[ParticipantRole] = mapped_column(
        String(50), default=ParticipantRole.Listener, nullable=False
    )
    invitation_status: Mapped[InvitationStatus] = mapped_column(
        String(50), default=InvitationStatus.Pending, nullable=False
    )
    consent_status: Mapped[ConsentStatus] = mapped_column(
        String(50), default=ConsentStatus.UNKNOWN, nullable=False
    )
    is_external: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    speaking_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    meeting = relationship("Meeting", back_populates="participants")


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False
    )
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False) # SHA-256
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    bitrate: Mapped[int] = mapped_column(Integer, nullable=False)
    codec: Mapped[str] = mapped_column(String(50), nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    channels: Mapped[int] = mapped_column(Integer, nullable=False)
    upload_status: Mapped[RecordingUploadStatus] = mapped_column(
        String(50), default=RecordingUploadStatus.Waiting, nullable=False
    )
    language_hint: Mapped[str] = mapped_column(String(50), default="en-US", nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(50), default="minio", nullable=False)
    encryption_key_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    meeting = relationship("Meeting", back_populates="recordings")
    transcripts = relationship("Transcript", back_populates="recording")

    def verify(self, checksum: str, duration_ms: int, bitrate: int, codec: str, sample_rate: int, channels: int) -> None:
        """Transition status to Verified. Enforces immutability after verification."""
        if self.upload_status == RecordingUploadStatus.Verified:
            raise ValueError("Cannot modify properties of an already verified recording")
        
        self.checksum = checksum
        self.duration_ms = duration_ms
        self.bitrate = bitrate
        self.codec = codec
        self.sample_rate = sample_rate
        self.channels = channels
        self.upload_status = RecordingUploadStatus.Verified
        self.uploaded_at = Clock.now()


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    aggregate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    metadata_block: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), name="metadata", nullable=False) # correlation_id, causation_id, trace_id, request_id, tenant_id
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False) # PENDING, PROCESSING, DELIVERED, FAILED, DEAD_LETTER
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    lease_locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class TranscriptStatus(str, enum.Enum):
    Queued = "Queued"
    Downloading = "Downloading"
    Transcribing = "Transcribing"
    Aligning = "Aligning"
    Persisting = "Persisting"
    Completed = "Completed"
    Failed = "Failed"


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False
    )
    recording_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recordings.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[TranscriptStatus] = mapped_column(
        String(50), default=TranscriptStatus.Queued, nullable=False
    )
    language_detected: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    meeting = relationship("Meeting", back_populates="transcripts")
    recording = relationship("Recording", back_populates="transcripts")
    utterances = relationship(
        "Utterance", back_populates="transcript", cascade="all, delete-orphan",
        order_by="Utterance.start_time"
    )
    speaker_identities = relationship(
        "SpeakerIdentity", back_populates="transcript", cascade="all, delete-orphan"
    )


class Utterance(Base):
    __tablename__ = "utterances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False
    )
    speaker_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(String(10000), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    transcript = relationship("Transcript", back_populates="utterances")
    words = relationship(
        "Word", back_populates="utterance", cascade="all, delete-orphan",
        order_by="Word.start_time"
    )


class Word(Base):
    __tablename__ = "words"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    utterance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("utterances.id", ondelete="CASCADE"),
        nullable=False
    )
    word: Mapped[str] = mapped_column(String(500), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    utterance = relationship("Utterance", back_populates="words")


class SpeakerIdentity(Base):
    """Maps anonymous diarization speaker tags to resolved participant identities."""
    __tablename__ = "speaker_identities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False
    )
    speaker_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    resolved_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    participant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    resolution_method: Mapped[str] = mapped_column(
        String(50), default="automatic", nullable=False
    )  # automatic, manual, voice_print

    transcript = relationship("Transcript", back_populates="speaker_identities")
    participant = relationship("Participant")


# ============================================================
# Phase 6: Meeting Intelligence Models & Enums
# ============================================================

class IntelligenceReportStatus(str, enum.Enum):
    Pending = "Pending"
    Processing = "Processing"
    Completed = "Completed"
    Failed = "Failed"


class ActionItemPriority(str, enum.Enum):
    High = "High"
    Medium = "Medium"
    Low = "Low"


class ActionItemStatus(str, enum.Enum):
    Pending = "Pending"
    InProgress = "InProgress"
    Completed = "Completed"
    Dismissed = "Dismissed"


class ConflictResolution(str, enum.Enum):
    Resolved = "Resolved"
    Unresolved = "Unresolved"
    Deferred = "Deferred"


class ArtifactReviewState(str, enum.Enum):
    Draft = "Draft"
    Validated = "Validated"
    NeedsReview = "NeedsReview"
    Approved = "Approved"
    Published = "Published"


class IntelligenceReport(Base):
    __tablename__ = "intelligence_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[IntelligenceReportStatus] = mapped_column(
        String(50), default=IntelligenceReportStatus.Pending, nullable=False
    )
    model_provider: Mapped[str] = mapped_column(String(100), default="mock", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0", nullable=False)
    processing_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    meeting = relationship("Meeting")
    transcript = relationship("Transcript")
    
    summaries = relationship("MeetingSummary", back_populates="report", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="report", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="report", cascade="all, delete-orphan")
    conflicts = relationship("Conflict", back_populates="report", cascade="all, delete-orphan")
    followups = relationship("Followup", back_populates="report", cascade="all, delete-orphan")


class IntelligenceArtifactBase:
    """Shared fields for all Artifact Store entities."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    review_state: Mapped[ArtifactReviewState] = mapped_column(
        String(50), default=ArtifactReviewState.Draft, nullable=False
    )
    
    # Provenance Evidence
    source_utterance_ids: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    source_word_ranges: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    
    # Multi-dimensional Confidence Value Object fields
    confidence_extraction: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence_grounding: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence_ownership: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence_temporal: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence_overall: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    model_provider: Mapped[str] = mapped_column(String(100), default="mock", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0", nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, onupdate=Clock.now, nullable=False
    )


class MeetingSummary(Base, IntelligenceArtifactBase):
    __tablename__ = "meeting_summaries"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intelligence_reports.id", ondelete="CASCADE"),
        nullable=False
    )
    executive_summary: Mapped[str] = mapped_column(String(10000), nullable=False)
    key_topics: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    outcomes: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    open_questions: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )

    report = relationship("IntelligenceReport", back_populates="summaries")


class ActionItem(Base, IntelligenceArtifactBase):
    __tablename__ = "action_items"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intelligence_reports.id", ondelete="CASCADE"),
        nullable=False
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    owner_speaker_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    owner_participant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True
    )
    deadline_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deadline_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[ActionItemPriority] = mapped_column(
        String(50), default=ActionItemPriority.Medium, nullable=False
    )
    status: Mapped[ActionItemStatus] = mapped_column(
        String(50), default=ActionItemStatus.Pending, nullable=False
    )
    external_system: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    external_object_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[Optional[str]] = mapped_column(String(50), default="IDLE", nullable=True)
    sync_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    report = relationship("IntelligenceReport", back_populates="action_items")
    owner_participant = relationship("Participant")
    project = relationship("Project", back_populates="tasks")


class Decision(Base, IntelligenceArtifactBase):
    __tablename__ = "decisions"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intelligence_reports.id", ondelete="CASCADE"),
        nullable=False
    )
    summary: Mapped[str] = mapped_column(String(4000), nullable=False)
    context: Mapped[str] = mapped_column(String(4000), nullable=False)
    rationale: Mapped[str] = mapped_column(String(4000), nullable=False)
    state: Mapped[DecisionState] = mapped_column(
        String(50), default=DecisionState.CONFIRMED, nullable=False
    )
    participants_involved: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    external_system: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    external_object_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[Optional[str]] = mapped_column(String(50), default="IDLE", nullable=True)
    sync_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    report = relationship("IntelligenceReport", back_populates="decisions")
    evidence_items = relationship("DecisionEvidence", back_populates="decision", cascade="all, delete-orphan")
    versions = relationship("DecisionVersion", foreign_keys="DecisionVersion.decision_id", back_populates="decision", cascade="all, delete-orphan")


class DecisionEvidence(Base):
    __tablename__ = "decision_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False
    )
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="SET NULL"),
        nullable=True
    )
    utterance_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("utterances.id", ondelete="SET NULL"),
        nullable=True
    )
    participant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True
    )
    start_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    end_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quote: Mapped[str] = mapped_column(String(4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )

    decision = relationship("Decision", back_populates="evidence_items")
    meeting = relationship("Meeting")
    participant = relationship("Participant")


class DecisionVersion(Base):
    __tablename__ = "decision_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state: Mapped[DecisionState] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(String(4000), nullable=False)
    rationale: Mapped[str] = mapped_column(String(4000), nullable=False)
    superseded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="SET NULL"),
        nullable=True
    )
    changed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )

    decision = relationship("Decision", foreign_keys=[decision_id], back_populates="versions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_value: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    new_value: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    metadata_block: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )


class Conflict(Base, IntelligenceArtifactBase):
    __tablename__ = "conflicts"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intelligence_reports.id", ondelete="CASCADE"),
        nullable=False
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    positions: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    resolution_status: Mapped[ConflictResolution] = mapped_column(
        String(50), default=ConflictResolution.Unresolved, nullable=False
    )
    resolution_summary: Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)

    report = relationship("IntelligenceReport", back_populates="conflicts")


class Followup(Base, IntelligenceArtifactBase):
    __tablename__ = "followups"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intelligence_reports.id", ondelete="CASCADE"),
        nullable=False
    )
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    suggested_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    related_action_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("action_items.id", ondelete="SET NULL"),
        nullable=True
    )

    report = relationship("IntelligenceReport", back_populates="followups")
    related_action_item = relationship("ActionItem")


# ============================================================
# Phase 7: Knowledge Index Models & Enums
# ============================================================

class IndexStatus(str, enum.Enum):
    Queued = "Queued"
    Chunking = "Chunking"
    Embedding = "Embedding"
    Persisting = "Persisting"
    Indexed = "Indexed"
    Failed = "Failed"


class IndexReport(Base):
    __tablename__ = "index_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[IndexStatus] = mapped_column(
        String(50), default=IndexStatus.Queued, nullable=False
    )
    indexing_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    meeting = relationship("Meeting")


class KnowledgeChunk(Base):
    """Immutable retrieval text chunks mapping back to primary database records."""
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # transcript, summary, action_item, decision, conflict, followup
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )  # e.g., utterance_id or action_item_id
    text_content: Mapped[str] = mapped_column(String(10000), nullable=False)
    metadata_block: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )

    meeting = relationship("Meeting")
    embeddings = relationship("KnowledgeEmbedding", back_populates="chunk", cascade="all, delete-orphan")


class KnowledgeEmbedding(Base):
    """Dense vector representations mapping back to KnowledgeChunks."""
    __tablename__ = "knowledge_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE"),
        nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), default="mock", nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, default=768, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    embedding_json: Mapped[str] = mapped_column(String(20000), nullable=False)  # JSON-string array of floats for DB portability
    text_checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 for duplicate detection
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )

    chunk = relationship("KnowledgeChunk", back_populates="embeddings")


class IntegrationConfig(Base):
    """Configuration mapping credentials and capabilities for external workspace targets."""
    __tablename__ = "integration_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'mock', 'slack', 'webhook'
    credentials_encrypted: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    capabilities: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )


class IntegrationOutbox(Base):
    """Tracks outbox task statuses, trace context, retries, and errors for external integrations."""
    __tablename__ = "integration_outbox"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Queued", nullable=False)  # Queued, Dispatching, Delivered, Retrying, DeadLetter, Cancelled
    payload: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=Clock.now, nullable=False
    )




