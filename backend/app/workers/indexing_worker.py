"""
Knowledge Index Background Worker

Consumes MeetingIntelligenceReady events, chunks transcripts and intelligence artifacts,
creates vector embeddings in batch, and commits them transactionally to the database.
"""
import uuid
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select

from app.core.clock import Clock
from app.models.meeting import (
    OutboxEvent, Meeting, Transcript, Utterance, IntelligenceReport,
    IndexReport, IndexStatus, MeetingSummary, ActionItem, Decision, Conflict, Followup
)
from app.services.knowledge import (
    EmbeddingEngine,
    MockEmbeddingEngine,
    KnowledgeIndexingService
)
from app.infrastructure.events import enqueue_outbox_event

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class IndexingWorker:
    """Consumes MeetingIntelligenceReady outbox events and executes text chunking & indexing."""

    def __init__(
        self,
        db_session_factory: sessionmaker,
        embedding_engine: Optional[EmbeddingEngine] = None,
        indexing_service: Optional[KnowledgeIndexingService] = None
    ):
        self.db_session_factory = db_session_factory
        self.embedding_engine = embedding_engine or MockEmbeddingEngine()
        self.service = indexing_service or KnowledgeIndexingService()
        self.is_running = False

    async def start(self, poll_interval: float = 2.0) -> None:
        self.is_running = True
        logger.info("Knowledge Indexing Worker started.")
        while self.is_running:
            try:
                processed = await self.poll_and_process()
                if not processed:
                    await asyncio.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Indexing worker error: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)

    async def stop(self) -> None:
        self.is_running = False
        logger.info("Knowledge Indexing Worker stopped.")

    async def poll_and_process(self) -> bool:
        """Checks outbox for completed intelligence reports ready for indexing."""
        with self.db_session_factory() as session:
            query = select(OutboxEvent).where(
                OutboxEvent.event_type == "MeetingIntelligenceReady",
                OutboxEvent.status == "DELIVERED",
            ).limit(1)
            result = session.execute(query)
            event = result.scalar_one_or_none()

            if not event:
                return False

            meeting_id = uuid.UUID(event.payload["meeting_id"])
            report_id = uuid.UUID(event.payload["report_id"])

            # Restore trace context if present in event metadata
            from app.core.tracing import TraceContextManager
            trace_id = event.metadata_block.get("trace_id")
            parent_span_id = event.metadata_block.get("span_id")
            if trace_id:
                # Generate worker span
                TraceContextManager.set_trace_context(trace_id, str(uuid.uuid4()), parent_span_id)

            # Check if index already completed for this meeting (Idempotency check)
            existing = session.query(IndexReport).filter(
                IndexReport.meeting_id == meeting_id
            ).first()

            if existing and existing.status == IndexStatus.Indexed:
                event.status = "CONSUMED"
                session.commit()
                TraceContextManager.clear_trace_context()
                return True

        # Process indexing
        import time
        from app.core.metrics import metrics_collector
        start_time = time.time()
        
        try:
            await self.run_indexing(meeting_id, report_id)
            duration_ms = (time.time() - start_time) * 1000
            metrics_collector.record_duration("indexing_pipeline_duration_seconds", duration_ms / 1000.0)
            metrics_collector.increment("embedding_tokens", 450)
        finally:
            TraceContextManager.clear_trace_context()
            
        return True

    async def run_indexing(self, meeting_id: uuid.UUID, report_id: uuid.UUID) -> None:
        """Executes full indexing stages: ChunkingStarted -> EmbeddingStarted -> IndexPersisted -> MeetingIndexed."""
        start_time = Clock.now()

        with self.db_session_factory() as session:
            # 1. Create Index report
            report = self.service.create_index_report(meeting_id, session)
            report_id_db = report.id
            self.service.update_status(report_id_db, IndexStatus.Chunking, session)

            # Emit Outbox Event ChunkingStarted
            enqueue_outbox_event(
                db_session=session,
                aggregate_id=meeting_id,
                aggregate_type="Meeting",
                event_type="ChunkingStarted",
                event_version=1,
                payload={"meeting_id": str(meeting_id), "report_id": str(report_id_db)},
                metadata_block={}
            )
            session.commit()

            # Load raw utterances
            transcript = session.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
            if not transcript:
                self.service.mark_failed(report_id_db, "Transcript not found", session)
                return

            utterances = session.query(Utterance).filter(Utterance.transcript_id == transcript.id).order_by(Utterance.start_time).all()

            # Load intelligence artifacts
            intel_report = session.query(IntelligenceReport).filter(IntelligenceReport.id == report_id).first()
            if not intel_report:
                self.service.mark_failed(report_id_db, "IntelligenceReport not found", session)
                return

            summaries = session.query(MeetingSummary).filter(MeetingSummary.report_id == report_id).all()
            action_items = session.query(ActionItem).filter(ActionItem.report_id == report_id).all()
            decisions = session.query(Decision).filter(Decision.report_id == report_id).all()
            conflicts = session.query(Conflict).filter(Conflict.report_id == report_id).all()
            followups = session.query(Followup).filter(Followup.report_id == report_id).all()

        try:
            chunks = []

            # A. Chunk contiguous utterances in groups of 15 (overlapping by 3)
            chunk_size = 15
            overlap = 3
            i = 0
            while i < len(utterances):
                window = utterances[i:i + chunk_size]
                if not window:
                    break
                
                text_block = "\n".join(f"{u.speaker_tag}: {u.text}" for u in window)
                chunk_meta = {
                    "start_time": window[0].start_time,
                    "end_time": window[-1].end_time,
                    "speaker_tags": list(set(u.speaker_tag for u in window))
                }
                chunks.append({
                    "source_type": "transcript",
                    "parent_id": window[0].id, # Immutable identifier pointing to first utterance
                    "text_content": text_block,
                    "metadata": chunk_meta
                })
                i += (chunk_size - overlap)

            # B. Chunk Summaries topics
            for summary in summaries:
                for topic in summary.key_topics:
                    chunks.append({
                        "source_type": "summary",
                        "parent_id": summary.id,
                        "text_content": f"Topic: {topic['topic']}. Details: {topic['summary']}",
                        "metadata": {"topic": topic["topic"]}
                    })

            # C. Chunk Action Items
            for action in action_items:
                chunks.append({
                    "source_type": "action_item",
                    "parent_id": action.id,
                    "text_content": f"Action Item: {action.title}. Task: {action.description}. Assignee: {action.owner_speaker_tag or 'Unassigned'}. Priority: {action.priority}",
                    "metadata": {"priority": action.priority, "owner": action.owner_speaker_tag}
                })

            # D. Chunk Decisions
            for dec in decisions:
                chunks.append({
                    "source_type": "decision",
                    "parent_id": dec.id,
                    "text_content": f"Decision: {dec.summary}. Context: {dec.context}. Rationale: {dec.rationale}.",
                    "metadata": {"participants": dec.participants_involved}
                })

            # E. Chunk Conflicts
            for con in conflicts:
                chunks.append({
                    "source_type": "conflict",
                    "parent_id": con.id,
                    "text_content": f"Conflict: {con.topic}. Stances: {json.dumps(con.positions)}. Resolution: {con.resolution_status}.",
                    "metadata": {"resolution_status": con.resolution_status}
                })

            # F. Chunk Followups
            for fol in followups:
                chunks.append({
                    "source_type": "followup",
                    "parent_id": fol.id,
                    "text_content": f"Followup: {fol.description}.",
                    "metadata": {}
                })

            if not chunks:
                with self.db_session_factory() as session:
                    report = session.query(IndexReport).filter(IndexReport.id == report_id_db).first()
                    report.status = IndexStatus.Indexed
                    report.completed_at = Clock.now()
                    session.commit()
                return

            # 2. EmbeddingStarted Stage
            with self.db_session_factory() as session:
                self.service.update_status(report_id_db, IndexStatus.Embedding, session)
                enqueue_outbox_event(
                    db_session=session,
                    aggregate_id=meeting_id,
                    aggregate_type="Meeting",
                    event_type="EmbeddingStarted",
                    event_version=1,
                    payload={"meeting_id": str(meeting_id), "report_id": str(report_id_db)},
                    metadata_block={}
                )
                session.commit()

            # Batch generate embeddings
            text_contents = [c["text_content"] for c in chunks]
            embeddings = self.embedding_engine.generate_embeddings_batch(text_contents)

            # 3. IndexPersisted Stage
            with self.db_session_factory() as session:
                self.service.update_status(report_id_db, IndexStatus.Persisting, session)
                self.service.save_indexed_chunks(
                    meeting_id=meeting_id,
                    chunks_data=chunks,
                    embeddings_data=embeddings,
                    model_name="mock",
                    dimension=768,
                    model_version="v1",
                    db_session=session
                )

                # Update completed IndexReport & emit events
                duration = int((Clock.now() - start_time).total_seconds() * 1000)
                report = session.query(IndexReport).filter(IndexReport.id == report_id_db).first()
                report.status = IndexStatus.Indexed
                report.indexing_duration_ms = duration
                report.completed_at = Clock.now()

                enqueue_outbox_event(
                    db_session=session,
                    aggregate_id=meeting_id,
                    aggregate_type="Meeting",
                    event_type="IndexPersisted",
                    event_version=1,
                    payload={"meeting_id": str(meeting_id), "report_id": str(report_id_db)},
                    metadata_block={}
                )

                enqueue_outbox_event(
                    db_session=session,
                    aggregate_id=meeting_id,
                    aggregate_type="Meeting",
                    event_type="MeetingIndexed",
                    event_version=1,
                    payload={"meeting_id": str(meeting_id), "report_id": str(report_id_db)},
                    metadata_block={}
                )
                session.commit()

            logger.info(f"Indexing completed successfully for report {report_id_db}.")

        except Exception as e:
            logger.error(f"Indexing failure: {e}", exc_info=True)
            with self.db_session_factory() as session:
                self.service.mark_failed(report_id_db, str(e), session)
