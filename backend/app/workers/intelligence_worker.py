"""
Meeting Intelligence Background Worker

Consumes TranscriptReady outbox events, executes the staged validation pipeline,
validates grounding source citations, computes multi-dimensional overall confidence,
gates review status, and persists intelligence artifacts.
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
    OutboxEvent, Transcript, Utterance, IntelligenceReport,
    IntelligenceReportStatus, ArtifactReviewState
)
from app.services.intelligence import (
    MeetingIntelligenceEngine,
    MockIntelligenceEngine,
    MeetingIntelligenceService
)
from app.core.metrics import metrics_collector

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


# Grounding Validator
def validate_grounding(citations: List[str], valid_utterance_ids: List[str]) -> bool:
    """Verifies that all LLM-extracted utterance IDs actually exist in the original transcript.

    Returns False if any cited utterance ID is missing from the database (hallucination).
    """
    if not citations:
        return False
    for citation in citations:
        if citation not in valid_utterance_ids:
            logger.warning(f"Grounding failure: Cited utterance {citation} not in valid database list.")
            return False
    return True


class IntelligenceWorker:
    """Stateless worker orchestrating the Staged Verification Pipeline."""

    def __init__(
        self,
        db_session_factory: sessionmaker,
        engine: Optional[MeetingIntelligenceEngine] = None,
        service: Optional[MeetingIntelligenceService] = None,
        metrics: Optional[Any] = None
    ):
        self.db_session_factory = db_session_factory
        self.engine = engine or MockIntelligenceEngine()
        self.service = service or MeetingIntelligenceService()
        self.metrics = metrics
        self.is_running = False

    async def start(self, poll_interval: float = 2.0) -> None:
        self.is_running = True
        logger.info("Meeting Intelligence Worker started.")
        while self.is_running:
            try:
                processed = await self.poll_and_process()
                if not processed:
                    await asyncio.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Intelligence worker error: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)

    async def stop(self) -> None:
        self.is_running = False
        logger.info("Meeting Intelligence Worker stopped.")

    async def poll_and_process(self) -> bool:
        """Polls for TranscriptReady event and initiates pipeline execution."""
        with self.db_session_factory() as session:
            query = select(OutboxEvent).where(
                OutboxEvent.event_type == "TranscriptReady",
                OutboxEvent.status == "DELIVERED",
            ).limit(1)
            result = session.execute(query)
            event = result.scalar_one_or_none()

            if not event:
                return False

            meeting_id = uuid.UUID(event.payload["meeting_id"])
            transcript_id = uuid.UUID(event.payload["transcript_id"])

            # Restore trace context if present in event metadata
            from app.core.tracing import TraceContextManager
            trace_id = event.metadata_block.get("trace_id")
            parent_span_id = event.metadata_block.get("span_id")
            if trace_id:
                # Generate worker span
                TraceContextManager.set_trace_context(trace_id, str(uuid.uuid4()), parent_span_id)

            # Check if report already exists (Idempotency)
            existing = session.query(IntelligenceReport).filter(
                IntelligenceReport.transcript_id == transcript_id
            ).first()

            if existing and existing.status == IntelligenceReportStatus.Completed:
                event.status = "CONSUMED"
                session.commit()
                TraceContextManager.clear_trace_context()
                return True

        # Run pipeline
        import time
        from app.core.metrics import metrics_collector
        start_time = time.time()
        
        try:
            await self.execute_pipeline(meeting_id, transcript_id)
            duration_ms = (time.time() - start_time) * 1000
            metrics_collector.record_duration("llm_generation_duration_ms", duration_ms)
            
            # Record simulated token usage & costs
            metrics_collector.increment("tokens_prompt", 1500)
            metrics_collector.increment("tokens_completion", 800)
            metrics_collector.increment("estimated_cost", 0.02)
        finally:
            TraceContextManager.clear_trace_context()
            
        return True

    async def execute_pipeline(self, meeting_id: uuid.UUID, transcript_id: uuid.UUID) -> None:
        """Staged Verification Pipeline: Builder -> Adapt -> Validate -> Score -> Persist."""
        start_time = Clock.now()

        with self.db_session_factory() as session:
            # Create report
            report = self.service.create_report(meeting_id, transcript_id, session)
            report_id = report.id
            self.service.mark_processing(report_id, session)

            # 1. Context Builder: Load transcript and utterances
            transcript = session.query(Transcript).filter(Transcript.id == transcript_id).first()
            if not transcript:
                self.service.mark_failed(report_id, "Transcript not found", session)
                return

            utterances = session.query(Utterance).filter(Utterance.transcript_id == transcript_id).all()
            valid_utterance_ids = [str(u.id) for u in utterances]
            utterance_list = [
                {
                    "id": str(u.id),
                    "speaker": u.speaker_tag,
                    "text": u.text,
                    "start": u.start_time,
                    "end": u.end_time
                }
                for u in utterances
            ]
            transcript_text = "\n".join(f"{u['speaker']}: {u['text']}" for u in utterance_list)

        try:
            # 2. Prompt Router & LLM Adapter: Invoke engine
            logger.info(f"Routing to LLM Engine for report {report_id}")
            raw_result = self.engine.process_transcript(transcript_text, utterance_list)

            # 3. JSON Schema Validation & Grounding Validator checks
            grounded_action_items = []
            grounded_decisions = []
            grounded_conflicts = []
            grounded_followups = []

            # Summary Gating & Grounding check
            summary_raw = raw_result["summary"]
            sum_citations = []
            for topic in summary_raw.get("key_topics", []):
                sum_citations.extend(topic.get("source_utterance_ids", []))
            
            summary_grounded = validate_grounding(sum_citations, valid_utterance_ids)
            sum_overall = summary_raw.get("confidence", 1.0)
            summary_raw["confidence_overall"] = sum_overall
            summary_raw["source_utterance_ids"] = sum_citations
            summary_raw["review_state"] = (
                ArtifactReviewState.Validated if (sum_overall >= 0.8 and summary_grounded)
                else ArtifactReviewState.NeedsReview
            )

            # Action Items Validation
            for item in raw_result.get("action_items", []):
                citations = item.get("source_utterance_ids", [])
                is_grounded = validate_grounding(citations, valid_utterance_ids)
                
                # Compute multi-dimensional overall confidence
                c_ext = item.get("confidence_extraction", 1.0)
                c_gro = item.get("confidence_grounding", 1.0)
                c_own = item.get("confidence_ownership", 1.0)
                c_tmp = item.get("confidence_temporal", 1.0)
                overall = round((c_ext + c_gro + c_own + c_tmp) / 4.0, 3)
                
                item["confidence_overall"] = overall
                # Gating Invariant: Must have action verb, owner, evidence, and overall conf >= 0.8
                has_owner = bool(item.get("owner_speaker_tag"))
                has_title = bool(item.get("title"))
                
                item["review_state"] = (
                    ArtifactReviewState.Validated if (overall >= 0.8 and is_grounded and has_owner and has_title)
                    else ArtifactReviewState.NeedsReview
                )
                grounded_action_items.append(item)

            # Decisions Validation
            for dec in raw_result.get("decisions", []):
                citations = dec.get("source_utterance_ids", [])
                is_grounded = validate_grounding(citations, valid_utterance_ids)
                c_ext = dec.get("confidence_extraction", 1.0)
                c_gro = dec.get("confidence_grounding", 1.0)
                overall = round((c_ext + c_gro) / 2.0, 3)
                
                dec["confidence_overall"] = overall
                has_summary = bool(dec.get("summary"))
                
                dec["review_state"] = (
                    ArtifactReviewState.Validated if (overall >= 0.8 and is_grounded and has_summary)
                    else ArtifactReviewState.NeedsReview
                )
                grounded_decisions.append(dec)

            # Conflicts Validation
            for con in raw_result.get("conflicts", []):
                citations = con.get("source_utterance_ids", [])
                is_grounded = validate_grounding(citations, valid_utterance_ids)
                c_ext = con.get("confidence_extraction", 1.0)
                c_gro = con.get("confidence_grounding", 1.0)
                overall = round((c_ext + c_gro) / 2.0, 3)
                
                con["confidence_overall"] = overall
                # Invariant: Conflict must have opposing stances and evidence
                has_positions = len(con.get("positions", [])) >= 2
                
                con["review_state"] = (
                    ArtifactReviewState.Validated if (overall >= 0.8 and is_grounded and has_positions)
                    else ArtifactReviewState.NeedsReview
                )
                grounded_conflicts.append(con)

            # Followups Validation
            for fol in raw_result.get("followups", []):
                citations = fol.get("source_utterance_ids", [])
                is_grounded = validate_grounding(citations, valid_utterance_ids)
                overall = fol.get("confidence_extraction", 1.0)
                
                fol["confidence_overall"] = overall
                fol["review_state"] = (
                    ArtifactReviewState.Validated if (overall >= 0.8 and is_grounded)
                    else ArtifactReviewState.NeedsReview
                )
                grounded_followups.append(fol)

            # Save Results
            duration_ms = int((Clock.now() - start_time).total_seconds() * 1000)
            with self.db_session_factory() as session:
                self.service.save_intelligence_results(
                    report_id=report_id,
                    summary_data=summary_raw,
                    action_items=grounded_action_items,
                    decisions=grounded_decisions,
                    conflicts=grounded_conflicts,
                    followups=grounded_followups,
                    model_provider="mock",
                    model_version="v1.0",
                    duration_ms=duration_ms,
                    db_session=session
                )
            
            logger.info(f"Intelligence processing completed for report {report_id}")

        except Exception as e:
            logger.error(f"Intelligence pipeline failure: {e}", exc_info=True)
            with self.db_session_factory() as session:
                self.service.mark_failed(report_id, str(e), session)
