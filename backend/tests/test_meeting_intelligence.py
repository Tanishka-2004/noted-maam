"""
Test Suite — Meeting Intelligence Bounded Context

Verifies:
  1. Database persistence of the unified Artifact Store schema (Summary, ActionItem, Decision, Conflict, Followup)
  2. Grounding validator catches invalid or missing utterance references
  3. Gating logic (low overall confidence flags items as NeedsReview)
  4. Integration worker pipeline: TranscriptReady -> Worker loop -> DB commit -> outbox events
"""
import uuid
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.clock import Clock
from app.models.auth import User, Workspace, Membership
from app.models.meeting import (
    Meeting, MeetingLifecycle, Recording, RecordingUploadStatus,
    Transcript, TranscriptStatus, Utterance, OutboxEvent,
    IntelligenceReport, IntelligenceReportStatus, ArtifactReviewState,
    MeetingSummary, ActionItem, Decision, Conflict, Followup, ActionItemPriority
)
from app.services.intelligence import MeetingIntelligenceService, MockIntelligenceEngine
from app.workers.intelligence_worker import IntelligenceWorker, validate_grounding

# Setup test SQLite DB
TEST_INT_DB_URL = "sqlite:///./test_intelligence.db"
engine = create_engine(TEST_INT_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db_session")
def fixture_db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _create_meeting_scaffolding(db_session):
    """Generates standard database elements to test intelligence pipeline dependencies."""
    user = User(id=uuid.uuid4(), email="int@example.com", password_hash="hash", is_active=True)
    workspace = Workspace(id=uuid.uuid4(), name="Intelligence Org")
    membership = Membership(user_id=user.id, workspace_id=workspace.id, role="Owner")
    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title="Intelligence Review Standup",
        created_by=user.id,
        lifecycle_state=MeetingLifecycle.Ended,
    )
    recording = Recording(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        s3_bucket="test-bucket",
        s3_key="test/recording.wav",
        original_filename="recording.wav",
        checksum="abc123",
        file_size=96000,
        duration_ms=3000,
        bitrate=256000,
        codec="audio/wav",
        sample_rate=16000,
        channels=1,
        upload_status=RecordingUploadStatus.Verified,
    )
    transcript = Transcript(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        recording_id=recording.id,
        status=TranscriptStatus.Completed,
    )
    u1 = Utterance(
        id=uuid.uuid4(),
        transcript_id=transcript.id,
        speaker_tag="SPEAKER_00",
        text="Rahul, please document the outbox table schema.",
        start_time=0.0,
        end_time=3.0,
        confidence=0.95
    )
    u2 = Utterance(
        id=uuid.uuid4(),
        transcript_id=transcript.id,
        speaker_tag="SPEAKER_01",
        text="Sure, I will handle that by Friday.",
        start_time=3.5,
        end_time=6.0,
        confidence=0.92
    )
    db_session.add_all([user, workspace, membership, meeting, recording, transcript, u1, u2])
    db_session.commit()
    return meeting, transcript, u1, u2


# ============================================================
# 1. Schema Hierarchy and Cascade Tests
# ============================================================

def test_intelligence_report_artifact_hierarchy(db_session):
    """Verifies that all specialized artifacts inherit baseline metadata and save properly."""
    meeting, transcript, u1, u2 = _create_meeting_scaffolding(db_session)

    report = IntelligenceReport(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        transcript_id=transcript.id,
        status=IntelligenceReportStatus.Completed,
        model_provider="mock",
        model_version="v1.0"
    )
    db_session.add(report)

    # Save summary
    summary = MeetingSummary(
        id=uuid.uuid4(),
        report_id=report.id,
        executive_summary="Executive review standup",
        key_topics=[{"topic": "Outbox", "summary": "Adopt outbox pattern"}],
        outcomes=["Adopted outbox"],
        open_questions=[],
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[str(u1.id)],
        confidence_overall=0.95
    )
    # Save Action Item
    action = ActionItem(
        id=uuid.uuid4(),
        report_id=report.id,
        title="Document schema",
        description="Write PostgreSQL/SQLite DDL",
        owner_speaker_tag="SPEAKER_00",
        priority=ActionItemPriority.High,
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[str(u1.id), str(u2.id)],
        confidence_overall=0.91,
        confidence_extraction=0.95,
        confidence_grounding=0.92,
        confidence_ownership=0.90,
        confidence_temporal=0.88
    )
    # Save Decision
    decision = Decision(
        id=uuid.uuid4(),
        report_id=report.id,
        summary="Adopt transactional outbox",
        context="Database sync fails caused lost events",
        rationale="Guarantees delivery consistency",
        participants_involved=["SPEAKER_00", "SPEAKER_01"],
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[str(u1.id)],
        confidence_overall=0.94
    )
    # Save Conflict
    conflict = Conflict(
        id=uuid.uuid4(),
        report_id=report.id,
        topic="Direct publish vs Outbox pattern",
        positions=[
            {"speaker": "SPEAKER_01", "stance": "Direct API is simpler"},
            {"speaker": "SPEAKER_00", "stance": "Outbox pattern is consistent"}
        ],
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[str(u1.id), str(u2.id)],
        confidence_overall=0.89
    )
    # Save Followup
    followup = Followup(
        id=uuid.uuid4(),
        report_id=report.id,
        description="Review outbox indexing",
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[str(u2.id)],
        confidence_overall=0.92
    )

    db_session.add_all([summary, action, decision, conflict, followup])
    db_session.commit()

    # Query back
    loaded_report = db_session.query(IntelligenceReport).filter(IntelligenceReport.id == report.id).first()
    assert loaded_report is not None
    assert len(loaded_report.summaries) == 1
    assert len(loaded_report.action_items) == 1
    assert len(loaded_report.decisions) == 1
    assert len(loaded_report.conflicts) == 1
    assert len(loaded_report.followups) == 1

    # Verify Baseline Inheritance Values
    assert loaded_report.action_items[0].review_state == ArtifactReviewState.Validated
    assert loaded_report.action_items[0].confidence_extraction == 0.95
    assert loaded_report.action_items[0].confidence_grounding == 0.92
    assert loaded_report.action_items[0].confidence_ownership == 0.90
    assert loaded_report.action_items[0].confidence_temporal == 0.88
    assert loaded_report.action_items[0].confidence_overall == 0.91


# ============================================================
# 2. Grounding & Gating Validation Pipeline Tests
# ============================================================

def test_grounding_validator():
    """Asserts that the Grounding Validator rejects non-existent utterance ID citations."""
    valid_ids = ["u1", "u2", "u3"]
    assert validate_grounding(["u1", "u2"], valid_ids) is True
    assert validate_grounding(["u1", "u4"], valid_ids) is False
    assert validate_grounding([], valid_ids) is False


def test_confidence_and_grounding_gating(db_session):
    """Verifies that low confidence scores or failed grounding citations flag items as NeedsReview."""
    meeting, transcript, u1, u2 = _create_meeting_scaffolding(db_session)
    valid_utterance_ids = [str(u1.id), str(u2.id)]

    # Scenario A: High Confidence & Valid Grounding citations
    assert validate_grounding([str(u1.id)], valid_utterance_ids) is True
    c_overall = 0.9

    # Artifact gets marked as Validated
    state_a = (
        ArtifactReviewState.Validated if (c_overall >= 0.8 and validate_grounding([str(u1.id)], valid_utterance_ids))
        else ArtifactReviewState.NeedsReview
    )
    assert state_a == ArtifactReviewState.Validated

    # Scenario B: Low Confidence overall (Overall confidence < 0.8 threshold)
    c_overall_low = 0.72
    state_b = (
        ArtifactReviewState.Validated if (c_overall_low >= 0.8 and validate_grounding([str(u1.id)], valid_utterance_ids))
        else ArtifactReviewState.NeedsReview
    )
    assert state_b == ArtifactReviewState.NeedsReview

    # Scenario C: Grounding Hallucination (Cited utterance ID doesn't exist)
    state_c = (
        ArtifactReviewState.Validated if (c_overall >= 0.8 and validate_grounding(["non-existent-uuid"], valid_utterance_ids))
        else ArtifactReviewState.NeedsReview
    )
    assert state_c == ArtifactReviewState.NeedsReview


# ============================================================
# 3. Service Layer Event flow Tests
# ============================================================

def test_service_lifecycle_and_events(db_session):
    """Verifies report creation, status transitions, and outbox event publishing."""
    meeting, transcript, _, _ = _create_meeting_scaffolding(db_session)
    service = MeetingIntelligenceService()

    report = service.create_report(meeting.id, transcript.id, db_session)
    assert report.status == IntelligenceReportStatus.Pending

    # Check outbox event for IntelligenceStarted
    outbox = db_session.query(OutboxEvent).filter(
        OutboxEvent.event_type == "IntelligenceStarted"
    ).first()
    assert outbox is not None
    assert outbox.payload["report_id"] == str(report.id)

    # Transition to processing
    service.mark_processing(report.id, db_session)
    assert report.status == IntelligenceReportStatus.Processing

    # Mock artifacts to save
    summary = {
        "executive_summary": "Review summary",
        "key_topics": [],
        "outcomes": [],
        "open_questions": [],
        "source_utterance_ids": [],
        "confidence_overall": 0.95,
        "review_state": ArtifactReviewState.Validated
    }

    # Save results and trigger final events
    service.save_intelligence_results(
        report_id=report.id,
        summary_data=summary,
        action_items=[],
        decisions=[],
        conflicts=[],
        followups=[],
        model_provider="mock",
        model_version="v1.0",
        duration_ms=120,
        db_session=db_session
    )

    assert report.status == IntelligenceReportStatus.Completed
    assert report.processing_duration_ms == 120

    # Verify event broadcasts
    validated_event = db_session.query(OutboxEvent).filter(
        OutboxEvent.event_type == "IntelligenceValidated"
    ).first()
    assert validated_event is not None

    ready_event = db_session.query(OutboxEvent).filter(
        OutboxEvent.event_type == "MeetingIntelligenceReady"
    ).first()
    assert ready_event is not None


# ============================================================
# 4. Mock Worker Integration pipeline test
# ============================================================

@pytest.mark.asyncio
async def test_worker_integration_pipeline(db_session):
    """Performs end-to-end integration test of worker loop.

    Asserts outbox event triggers staged worker run, mock engine completes,
    and artifacts are committed to database.
    """
    meeting, transcript, u1, u2 = _create_meeting_scaffolding(db_session)

    # Setup the outbox event for TranscriptReady
    event = OutboxEvent(
        id=uuid.uuid4(),
        event_uuid=uuid.uuid4(),
        aggregate_id=meeting.id,
        aggregate_type="Meeting",
        event_type="TranscriptReady",
        event_version=1,
        payload={"meeting_id": str(meeting.id), "transcript_id": str(transcript.id)},
        metadata_block={},
        status="DELIVERED",
        occurred_at=Clock.now()
    )
    db_session.add(event)
    db_session.commit()

    # Create worker with MockEngine
    worker = IntelligenceWorker(
        db_session_factory=lambda: TestingSessionLocal()
    )

    # Process event
    processed = await worker.poll_and_process()
    assert processed is True

    # Check report was created and completed
    report = db_session.query(IntelligenceReport).filter(
        IntelligenceReport.transcript_id == transcript.id
    ).first()
    assert report is not None
    assert report.status == IntelligenceReportStatus.Completed

    # Check artifacts are populated inside the store
    assert len(report.summaries) == 1
    assert len(report.action_items) == 1
    assert len(report.decisions) == 1
    assert len(report.conflicts) == 1
    assert len(report.followups) == 1

    # Check action item title and priority match mock output
    assert report.action_items[0].title == "Document outbox table schemas"
    assert report.action_items[0].priority == ActionItemPriority.High
    assert report.action_items[0].review_state == ArtifactReviewState.Validated


def test_service_mark_failed_and_retry(db_session):
    """Verifies that mark_failed records errors, increments retries, and broadcasts event."""
    meeting, transcript, _, _ = _create_meeting_scaffolding(db_session)
    service = MeetingIntelligenceService()

    report = service.create_report(meeting.id, transcript.id, db_session)
    service.mark_failed(report.id, "LLM rate limit error", db_session)

    refreshed = db_session.query(IntelligenceReport).filter(IntelligenceReport.id == report.id).first()
    assert refreshed.status == IntelligenceReportStatus.Failed
    assert refreshed.error_message == "LLM rate limit error"
    assert refreshed.retry_count == 1

    # Check outbox event
    failed_event = db_session.query(OutboxEvent).filter(
        OutboxEvent.event_type == "IntelligenceFailed"
    ).first()
    assert failed_event is not None
    assert failed_event.payload["error"] == "LLM rate limit error"


def test_mock_engine_process_transcript():
    """Verifies that MockIntelligenceEngine parses inputs and structures returns with default uuid fallbacks."""
    engine = MockIntelligenceEngine()
    result = engine.process_transcript("SPEAKER_00: Hello", [])
    assert "summary" in result
    assert result["summary"]["confidence"] == 0.95
    assert len(result["action_items"]) == 1
    assert result["action_items"][0]["owner_speaker_tag"] == "SPEAKER_00"


@pytest.mark.asyncio
async def test_worker_exception_handling(db_session):
    """Verifies that the worker handles failures gracefully, transitions reports to Failed, and increments retries."""
    meeting, transcript, _, _ = _create_meeting_scaffolding(db_session)

    # Trigger event
    event = OutboxEvent(
        id=uuid.uuid4(),
        event_uuid=uuid.uuid4(),
        aggregate_id=meeting.id,
        aggregate_type="Meeting",
        event_type="TranscriptReady",
        event_version=1,
        payload={"meeting_id": str(meeting.id), "transcript_id": str(transcript.id)},
        metadata_block={},
        status="DELIVERED",
        occurred_at=Clock.now()
    )
    db_session.add(event)
    db_session.commit()

    # Create breaking engine
    class BadEngine(MockIntelligenceEngine):
        def process_transcript(self, transcript_text, utterances):
            raise RuntimeError("LLM rate limits exceeded")

    worker = IntelligenceWorker(
        db_session_factory=lambda: TestingSessionLocal(),
        engine=BadEngine()
    )

    processed = await worker.poll_and_process()
    assert processed is True

    # Check report was marked Failed
    report = db_session.query(IntelligenceReport).filter(
        IntelligenceReport.transcript_id == transcript.id
    ).first()
    assert report is not None
    assert report.status == IntelligenceReportStatus.Failed
    assert report.retry_count == 1
    assert "LLM rate limits exceeded" in report.error_message


@pytest.mark.asyncio
async def test_worker_idempotency_handling(db_session):
    """Verifies that the worker marks the outbox event as CONSUMED if a completed report already exists."""
    meeting, transcript, _, _ = _create_meeting_scaffolding(db_session)

    # Pre-populate completed report
    report = IntelligenceReport(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        transcript_id=transcript.id,
        status=IntelligenceReportStatus.Completed,
        model_provider="mock",
        model_version="v1.0"
    )
    # Event
    event = OutboxEvent(
        id=uuid.uuid4(),
        event_uuid=uuid.uuid4(),
        aggregate_id=meeting.id,
        aggregate_type="Meeting",
        event_type="TranscriptReady",
        event_version=1,
        payload={"meeting_id": str(meeting.id), "transcript_id": str(transcript.id)},
        metadata_block={},
        status="DELIVERED",
        occurred_at=Clock.now()
    )
    db_session.add_all([report, event])
    db_session.commit()

    worker = IntelligenceWorker(db_session_factory=lambda: TestingSessionLocal())
    processed = await worker.poll_and_process()
    assert processed is True

    # Verify event status is CONSUMED
    db_session.refresh(event)
    assert event.status == "CONSUMED"


@pytest.mark.asyncio
async def test_worker_start_stop():
    """Verifies starting and stopping the background polling task of the worker."""
    worker = IntelligenceWorker(db_session_factory=lambda: TestingSessionLocal())
    
    # Start task in background
    task = asyncio.create_task(worker.start(poll_interval=0.1))
    await asyncio.sleep(0.15)
    
    assert worker.is_running is True
    await worker.stop()
    assert worker.is_running is False
    
    # Let task exit clean
    await task



