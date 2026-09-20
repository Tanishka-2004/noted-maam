"""
Test Suite — Knowledge Index Bounded Context

Verifies:
  1. Immutable chunking boundaries and source type assignments
  2. MockEmbeddingEngine returns deterministic vector lengths
  3. Incremental indexing overwrites existing meeting records cleanly (idempotency)
  4. Hybrid Searcher merges BM25 and vector similarities via Reciprocal Rank Fusion (RRF)
  5. Citation Validator gates workspace scopes and filters deleted entities
  6. IndexingWorker executes fully: MeetingIntelligenceReady -> IndexReport -> MeetingIndexed
"""
import uuid
import json
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
    MeetingSummary, ActionItem, Decision, Conflict, Followup, ActionItemPriority,
    IndexReport, IndexStatus, KnowledgeChunk, KnowledgeEmbedding
)
from app.services.knowledge import (
    KnowledgeIndexingService,
    KnowledgeRetrievalService,
    MockEmbeddingEngine,
    MockRerankerEngine
)
from app.workers.indexing_worker import IndexingWorker

# Setup isolated test database
TEST_KNOWLEDGE_DB = "sqlite:///./test_knowledge.db"
engine = create_engine(TEST_KNOWLEDGE_DB, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db_session")
def fixture_db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _setup_workspace_and_meeting(db_session):
    """Sets up primary workspace, users, meetings, transcript, and intelligence artifacts scaffolding."""
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
    transcript = Transcript(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        recording_id=uuid.uuid4(),
        status=TranscriptStatus.Completed,
    )
    u1 = Utterance(
        id=uuid.uuid4(),
        transcript_id=transcript.id,
        speaker_tag="SPEAKER_00",
        text="Adopt transactional outbox pattern to keep events consistent.",
        start_time=0.0,
        end_time=3.0,
        confidence=0.95
    )
    u2 = Utterance(
        id=uuid.uuid4(),
        transcript_id=transcript.id,
        speaker_tag="SPEAKER_01",
        text="I agree, we should not publish directly to Redis streams inside standard web request context.",
        start_time=3.2,
        end_time=6.5,
        confidence=0.93
    )
    intel_report = IntelligenceReport(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        transcript_id=transcript.id,
        status=IntelligenceReportStatus.Completed
    )
    summary = MeetingSummary(
        id=uuid.uuid4(),
        report_id=intel_report.id,
        executive_summary="Aligining architecture design",
        key_topics=[{"topic": "Design", "summary": "Detailed outbox design"}],
        outcomes=[],
        open_questions=[],
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[str(u1.id)],
        confidence_overall=0.9
    )
    action = ActionItem(
        id=uuid.uuid4(),
        report_id=intel_report.id,
        title="Document schema",
        description="Write PostgreSQL schema",
        owner_speaker_tag="SPEAKER_00",
        priority=ActionItemPriority.High,
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[str(u1.id)]
    )
    decision = Decision(
        id=uuid.uuid4(),
        report_id=intel_report.id,
        summary="Use transactional outbox pattern",
        context="Database commits succeed but network errors lose Redis stream broadcasts",
        rationale="Transactional table commits guarantee event deliveries",
        participants_involved=["SPEAKER_00", "SPEAKER_01"],
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[str(u1.id), str(u2.id)]
    )
    conflict = Conflict(
        id=uuid.uuid4(),
        report_id=intel_report.id,
        topic="Outbox vs Direct Stream",
        positions=[{"speaker": "SPEAKER_00", "stance": "Outbox is better"}],
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[str(u1.id)]
    )
    followup = Followup(
        id=uuid.uuid4(),
        report_id=intel_report.id,
        description="Verify performance benchmarks",
        review_state=ArtifactReviewState.Validated,
        source_utterance_ids=[str(u2.id)]
    )

    db_session.add_all([
        user, workspace, membership, meeting, transcript, u1, u2, 
        intel_report, summary, action, decision, conflict, followup
    ])
    db_session.commit()
    return user, workspace, meeting, transcript, u1, u2, intel_report, decision


# ============================================================
# 1. Engine & Chunking Tests
# ============================================================

def test_mock_embedding_generation():
    """Asserts MockEmbeddingEngine returns consistent dimension arrays and deterministic text mappings."""
    engine = MockEmbeddingEngine(dimension=768)
    e1 = engine.generate_embedding("Adopt outbox pattern")
    e2 = engine.generate_embedding("Adopt outbox pattern")
    e3 = engine.generate_embedding("Different text")

    assert len(e1) == 768
    assert e1 == e2  # Determinism check
    assert e1 != e3  # Distinct text mappings check


# ============================================================
# 2. Service Layer & Idempotent Indexing Tests
# ============================================================

def test_idempotent_indexing(db_session):
    """Verifies that indexing a meeting twice deletes old chunks and embeddings, avoiding duplicates."""
    _, _, meeting, _, _, _, _, _ = _setup_workspace_and_meeting(db_session)
    service = KnowledgeIndexingService()

    chunks_a = [
        {"source_type": "transcript", "parent_id": uuid.uuid4(), "text_content": "Text chunk A"}
    ]
    embeddings_a = [[0.1] * 768]

    # First Run
    service.save_indexed_chunks(
        meeting_id=meeting.id,
        chunks_data=chunks_a,
        embeddings_data=embeddings_a,
        model_name="mock",
        dimension=768,
        model_version="v1",
        db_session=db_session
    )

    c_count = db_session.query(KnowledgeChunk).filter(KnowledgeChunk.meeting_id == meeting.id).count()
    e_count = db_session.query(KnowledgeEmbedding).join(KnowledgeChunk).filter(
        KnowledgeChunk.meeting_id == meeting.id
    ).count()

    assert c_count == 1
    assert e_count == 1

    # Second Run (Replacement)
    chunks_b = [
        {"source_type": "transcript", "parent_id": uuid.uuid4(), "text_content": "Text chunk B1"},
        {"source_type": "decision", "parent_id": uuid.uuid4(), "text_content": "Text chunk B2"}
    ]
    embeddings_b = [[0.2] * 768, [0.3] * 768]

    service.save_indexed_chunks(
        meeting_id=meeting.id,
        chunks_data=chunks_b,
        embeddings_data=embeddings_b,
        model_name="mock",
        dimension=768,
        model_version="v1",
        db_session=db_session
    )

    c_count_new = db_session.query(KnowledgeChunk).filter(KnowledgeChunk.meeting_id == meeting.id).count()
    e_count_new = db_session.query(KnowledgeEmbedding).join(KnowledgeChunk).filter(
        KnowledgeChunk.meeting_id == meeting.id
    ).count()

    # Old records must have been pruned transactionally
    assert c_count_new == 2
    assert e_count_new == 2


# ============================================================
# 3. Hybrid Search & Workspace Isolation Tests
# ============================================================

def test_hybrid_search_rrf_and_workspace_isolation(db_session):
    """Verifies hybrid RRF search matches workspace bounds and citation validator rules."""
    user, workspace, meeting, _, u1, u2, _, _ = _setup_workspace_and_meeting(db_session)
    service = KnowledgeIndexingService()
    retriever = KnowledgeRetrievalService()

    # Pre-populate index chunks for meeting
    chunks = [
        {"source_type": "transcript", "parent_id": u1.id, "text_content": "Adopt transactional outbox pattern to keep events consistent."},
        {"source_type": "transcript", "parent_id": u2.id, "text_content": "I agree, we should not publish directly to Redis streams."}
    ]
    embeddings = [
        [0.1] * 768,
        [0.2] * 768
    ]

    service.save_indexed_chunks(
        meeting_id=meeting.id,
        chunks_data=chunks,
        embeddings_data=embeddings,
        model_name="mock",
        dimension=768,
        model_version="v1",
        db_session=db_session
    )

    # Pre-populate index report
    report = service.create_index_report(meeting.id, db_session)
    service.update_status(report.id, IndexStatus.Indexed, db_session)

    # Search Case A: Matches Workspace Access
    res_data = retriever.search_workspace(
        query="outbox pattern",
        user_id=user.id,
        workspace_id=workspace.id,
        db_session=db_session,
        limit=5
    )

    results = res_data["results"]
    assert res_data["answer_mode"] == "ANSWERABLE"
    assert len(results) >= 1
    assert results[0]["source_type"] == "transcript"
    assert "outbox" in results[0]["text_content"]

    # Search Case B: Rejects Outside Workspace
    other_workspace_id = uuid.uuid4()
    results_empty = retriever.search_workspace(
        query="outbox pattern",
        user_id=user.id,
        workspace_id=other_workspace_id,
        db_session=db_session,
        limit=5
    )
    assert results_empty["answer_mode"] == "UNKNOWN"
    assert len(results_empty["results"]) == 0


def test_citation_validator_filters_deleted_entities(db_session):
    """Asserts that the citation validator filters out chunks referencing deleted database entities."""
    user, workspace, meeting, _, u1, u2, _, _ = _setup_workspace_and_meeting(db_session)
    service = KnowledgeIndexingService()
    retriever = KnowledgeRetrievalService()

    # Pre-populate index chunks
    chunks = [
        {"source_type": "transcript", "parent_id": u1.id, "text_content": "Adopt transactional outbox pattern to keep events consistent."}
    ]
    embeddings = [[0.1] * 768]

    service.save_indexed_chunks(
        meeting_id=meeting.id,
        chunks_data=chunks,
        embeddings_data=embeddings,
        model_name="mock",
        dimension=768,
        model_version="v1",
        db_session=db_session
    )

    # Delete the cited utterance from primary database
    from sqlalchemy import delete
    db_session.execute(delete(Utterance).where(Utterance.id == u1.id))
    db_session.commit()

    # Search query
    res_data = retriever.search_workspace(
        query="outbox",
        user_id=user.id,
        workspace_id=workspace.id,
        db_session=db_session,
        limit=5
    )

    # Citations Validator must reject it since u1 no longer exists in primary DB
    assert res_data["answer_mode"] == "UNKNOWN"
    assert len(res_data["results"]) == 0


# ============================================================
# 4. Indexing Worker Integration Tests
# ============================================================

@pytest.mark.asyncio
async def test_indexing_worker_pipeline(db_session):
    """Verifies worker consummation loop: chunks text, creates embeddings, commits, and broadcasts MeetingIndexed."""
    user, workspace, meeting, transcript, u1, u2, intel_report, decision = _setup_workspace_and_meeting(db_session)

    # Emit MeetingIntelligenceReady event
    event = OutboxEvent(
        id=uuid.uuid4(),
        event_uuid=uuid.uuid4(),
        aggregate_id=meeting.id,
        aggregate_type="Meeting",
        event_type="MeetingIntelligenceReady",
        event_version=1,
        payload={"meeting_id": str(meeting.id), "report_id": str(intel_report.id)},
        metadata_block={},
        status="DELIVERED",
        occurred_at=Clock.now()
    )
    db_session.add(event)
    db_session.commit()

    # Instantiate worker
    worker = IndexingWorker(
        db_session_factory=lambda: TestingSessionLocal()
    )

    # Run polling loop
    processed = await worker.poll_and_process()
    assert processed is True

    # Assert IndexReport was finalized
    report = db_session.query(IndexReport).filter(IndexReport.meeting_id == meeting.id).first()
    assert report is not None
    assert report.status == IndexStatus.Indexed

    # Check chunks and embeddings exist
    chunks = db_session.query(KnowledgeChunk).filter(KnowledgeChunk.meeting_id == meeting.id).all()
    assert len(chunks) > 0

    # Ensure source types include transcript chunks and decision chunks
    sources = [c.source_type for c in chunks]
    assert "transcript" in sources
    assert "decision" in sources

    # Check outbox event emissions
    indexed_event = db_session.query(OutboxEvent).filter(
        OutboxEvent.event_type == "MeetingIndexed"
    ).first()
    assert indexed_event is not None


@pytest.mark.asyncio
async def test_indexing_worker_start_stop():
    """Verifies starting and stopping the background polling task of the indexing worker."""
    worker = IndexingWorker(db_session_factory=lambda: TestingSessionLocal())
    task = asyncio.create_task(worker.start(poll_interval=0.1))
    await asyncio.sleep(0.15)
    assert worker.is_running is True
    await worker.stop()
    assert worker.is_running is False
    await task


@pytest.mark.asyncio
async def test_indexing_worker_failure_flow(db_session):
    """Verifies that indexing worker failure transitions status to Failed and records errors."""
    user, workspace, meeting, transcript, u1, u2, intel_report, decision = _setup_workspace_and_meeting(db_session)
    event = OutboxEvent(
        id=uuid.uuid4(),
        event_uuid=uuid.uuid4(),
        aggregate_id=meeting.id,
        aggregate_type="Meeting",
        event_type="MeetingIntelligenceReady",
        event_version=1,
        payload={"meeting_id": str(meeting.id), "report_id": str(intel_report.id)},
        metadata_block={},
        status="DELIVERED",
        occurred_at=Clock.now()
    )
    db_session.add(event)
    db_session.commit()

    # Stub engine that raises an exception
    class BadEmbedEngine(MockEmbeddingEngine):
        def generate_embeddings_batch(self, texts):
            raise RuntimeError("API quota limits hit")

    worker = IndexingWorker(
        db_session_factory=lambda: TestingSessionLocal(),
        embedding_engine=BadEmbedEngine()
    )

    processed = await worker.poll_and_process()
    assert processed is True

    # Assert IndexReport failed
    report = db_session.query(IndexReport).filter(IndexReport.meeting_id == meeting.id).first()
    assert report is not None
    assert report.status == IndexStatus.Failed
    assert "API quota limits hit" in report.error_message
    assert report.retry_count == 1


@pytest.mark.asyncio
async def test_indexing_worker_missing_transcript(db_session):
    """Verifies that indexing worker fails gracefully when the meeting transcript is missing."""
    user, workspace, meeting, transcript, u1, u2, intel_report, decision = _setup_workspace_and_meeting(db_session)
    
    # Delete transcript to trigger failure path
    from sqlalchemy import delete
    db_session.execute(delete(Transcript).where(Transcript.id == transcript.id))
    db_session.commit()

    event = OutboxEvent(
        id=uuid.uuid4(),
        event_uuid=uuid.uuid4(),
        aggregate_id=meeting.id,
        aggregate_type="Meeting",
        event_type="MeetingIntelligenceReady",
        event_version=1,
        payload={"meeting_id": str(meeting.id), "report_id": str(intel_report.id)},
        metadata_block={},
        status="DELIVERED",
        occurred_at=Clock.now()
    )
    db_session.add(event)
    db_session.commit()

    worker = IndexingWorker(db_session_factory=lambda: TestingSessionLocal())
    await worker.poll_and_process()

    report = db_session.query(IndexReport).filter(IndexReport.meeting_id == meeting.id).first()
    assert report is not None
    assert report.status == IndexStatus.Failed
    assert "Transcript not found" in report.error_message


@pytest.mark.asyncio
async def test_indexing_worker_missing_intel_report(db_session):
    """Verifies that indexing worker fails gracefully when the meeting intelligence report is missing."""
    user, workspace, meeting, transcript, u1, u2, intel_report, decision = _setup_workspace_and_meeting(db_session)
    
    # Delete intelligence report to trigger failure path
    from sqlalchemy import delete
    db_session.execute(delete(IntelligenceReport).where(IntelligenceReport.id == intel_report.id))
    db_session.commit()

    event = OutboxEvent(
        id=uuid.uuid4(),
        event_uuid=uuid.uuid4(),
        aggregate_id=meeting.id,
        aggregate_type="Meeting",
        event_type="MeetingIntelligenceReady",
        event_version=1,
        payload={"meeting_id": str(meeting.id), "report_id": str(intel_report.id)},
        metadata_block={},
        status="DELIVERED",
        occurred_at=Clock.now()
    )
    db_session.add(event)
    db_session.commit()

    worker = IndexingWorker(db_session_factory=lambda: TestingSessionLocal())
    await worker.poll_and_process()

    report = db_session.query(IndexReport).filter(IndexReport.meeting_id == meeting.id).first()
    assert report is not None
    assert report.status == IndexStatus.Failed
    assert "IntelligenceReport not found" in report.error_message


