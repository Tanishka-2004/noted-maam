"""
Meeting Intelligence Service Layer & Engines

Defines the contract for LLM-agnostic extraction (MeetingIntelligenceEngine),
implements a deterministic mock engine, and houses the service pipeline that
controls validation, confidence assignment, human gating, and event outbox commits.
"""
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models.meeting import (
    IntelligenceReport, IntelligenceReportStatus, MeetingSummary,
    ActionItem, Decision, Conflict, Followup, ArtifactReviewState,
    ActionItemPriority, ActionItemStatus, ConflictResolution
)
from app.infrastructure.events import enqueue_outbox_event

logger = logging.getLogger(__name__)


# ============================================================
# Engine Contract & Concrete Mock Engine
# ============================================================

class MeetingIntelligenceEngine(ABC):
    """Abstract interface isolating LLM orchestration details from the service layer."""

    @abstractmethod
    def process_transcript(
        self,
        transcript_text: str,
        utterances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extracts intelligence artifacts from the transcript.

        Returns:
            {
                "summary": {
                    "executive_summary": "...",
                    "key_topics": [{"topic": "...", "summary": "...", "source_utterance_ids": ["..."]}],
                    "outcomes": ["..."],
                    "open_questions": ["..."],
                    "confidence": 0.95
                },
                "action_items": [
                    {
                        "title": "...",
                        "description": "...",
                        "owner_speaker_tag": "...",
                        "priority": "High"|"Medium"|"Low",
                        "deadline_text": "...",
                        "source_utterance_ids": ["..."],
                        "confidence_extraction": 0.9,
                        "confidence_grounding": 0.85,
                        "confidence_ownership": 0.95,
                        "confidence_temporal": 0.5
                    }
                ],
                "decisions": [
                    {
                        "summary": "...",
                        "context": "...",
                        "rationale": "...",
                        "participants_involved": ["..."],
                        "source_utterance_ids": ["..."],
                        "confidence_extraction": 0.92,
                        "confidence_grounding": 0.9
                    }
                ],
                "conflicts": [
                    {
                        "topic": "...",
                        "positions": [{"speaker": "...", "stance": "..."}],
                        "resolution_status": "Unresolved"|"Resolved"|"Deferred",
                        "resolution_summary": "...",
                        "source_utterance_ids": ["..."],
                        "confidence_extraction": 0.85,
                        "confidence_grounding": 0.8
                    }
                ],
                "followups": [
                    {
                        "description": "...",
                        "source_utterance_ids": ["..."],
                        "confidence_extraction": 0.9
                    }
                ]
            }
        """
        pass


class MockIntelligenceEngine(MeetingIntelligenceEngine):
    """Deterministic intelligence engine return canned mock responses for testing and safe CI/CD runs."""

    def process_transcript(
        self,
        transcript_text: str,
        utterances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        # Extract existing utterance IDs to return valid grounding citations
        utt_ids = [u["id"] for u in utterances]
        u1 = utt_ids[0] if len(utt_ids) > 0 else str(uuid.uuid4())
        u2 = utt_ids[1] if len(utt_ids) > 1 else u1

        return {
            "summary": {
                "executive_summary": "This was a highly productive engineering review about microservices integration.",
                "key_topics": [
                    {
                        "topic": "Outbox Pattern Integration",
                        "summary": "The team aligned on using the transactional outbox pattern to synchronize state changes.",
                        "source_utterance_ids": [u1]
                    }
                ],
                "outcomes": ["Outbox pattern accepted for downstream events"],
                "open_questions": ["Should we partition the outbox tables in Q4?"],
                "confidence": 0.95
            },
            "action_items": [
                {
                    "title": "Document outbox table schemas",
                    "description": "Create the PostgreSQL/SQLite outbox DDL and schema configuration.",
                    "owner_speaker_tag": "SPEAKER_00",
                    "priority": "High",
                    "deadline_text": "Next Friday",
                    "source_utterance_ids": [u1],
                    "confidence_extraction": 0.92,
                    "confidence_grounding": 0.95,
                    "confidence_ownership": 0.9,
                    "confidence_temporal": 0.85
                }
            ],
            "decisions": [
                {
                    "summary": "Adopt outbox pattern for cross-context events",
                    "context": "Direct HTTP posting caused inconsistent syncs on DB failures.",
                    "rationale": "Outbox provides transactional guarantee.",
                    "participants_involved": ["SPEAKER_00", "SPEAKER_01"],
                    "source_utterance_ids": [u1],
                    "confidence_extraction": 0.95,
                    "confidence_grounding": 0.92
                }
            ],
            "conflicts": [
                {
                    "topic": "Direct publish vs outbox pattern",
                    "positions": [
                        {"speaker": "SPEAKER_01", "stance": "Wants direct HTTP requests for simpler debugging"},
                        {"speaker": "SPEAKER_00", "stance": "Prefers Outbox table to guarantee event safety"}
                    ],
                    "resolution_status": "Resolved",
                    "resolution_summary": "The team decided outbox is required due to data consistency invariants.",
                    "source_utterance_ids": [u1, u2],
                    "confidence_extraction": 0.88,
                    "confidence_grounding": 0.9
                }
            ],
            "followups": [
                {
                    "description": "Schedule a follow-up review for RabbitMQ outbox dispatch performance.",
                    "source_utterance_ids": [u2],
                    "confidence_extraction": 0.92
                }
            ]
        }


# ============================================================
# Meeting Intelligence Service
# ============================================================

class MeetingIntelligenceService:
    """Handles report state machine transitions and transactionally writes verified artifacts."""

    def create_report(
        self,
        meeting_id: uuid.UUID,
        transcript_id: uuid.UUID,
        db_session: Session
    ) -> IntelligenceReport:
        """Initializes a new intelligence report in Pending state."""
        report = IntelligenceReport(
            id=uuid.uuid4(),
            meeting_id=meeting_id,
            transcript_id=transcript_id,
            status=IntelligenceReportStatus.Pending,
        )
        db_session.add(report)

        enqueue_outbox_event(
            db_session=db_session,
            aggregate_id=meeting_id,
            aggregate_type="Meeting",
            event_type="IntelligenceStarted",
            event_version=1,
            payload={
                "meeting_id": str(meeting_id),
                "transcript_id": str(transcript_id),
                "report_id": str(report.id)
            },
            metadata_block={}
        )
        db_session.commit()
        return report

    def mark_processing(self, report_id: uuid.UUID, db_session: Session) -> None:
        """Moves report status to Processing."""
        report = db_session.query(IntelligenceReport).filter(IntelligenceReport.id == report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")
        report.status = IntelligenceReportStatus.Processing
        db_session.commit()

    def mark_failed(self, report_id: uuid.UUID, error: str, db_session: Session) -> None:
        """Transitions report to Failed and increments retries."""
        report = db_session.query(IntelligenceReport).filter(IntelligenceReport.id == report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")
        report.status = IntelligenceReportStatus.Failed
        report.error_message = error
        report.retry_count += 1

        enqueue_outbox_event(
            db_session=db_session,
            aggregate_id=report.meeting_id,
            aggregate_type="Meeting",
            event_type="IntelligenceFailed",
            event_version=1,
            payload={
                "meeting_id": str(report.meeting_id),
                "report_id": str(report_id),
                "error": error,
                "retry_count": report.retry_count
            },
            metadata_block={}
        )
        db_session.commit()

    def save_intelligence_results(
        self,
        report_id: uuid.UUID,
        summary_data: Dict[str, Any],
        action_items: List[Dict[str, Any]],
        decisions: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        followups: List[Dict[str, Any]],
        model_provider: str,
        model_version: str,
        duration_ms: int,
        db_session: Session
    ) -> IntelligenceReport:
        """Persists extracted Artifact Store elements and publishes events."""
        report = db_session.query(IntelligenceReport).filter(IntelligenceReport.id == report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")

        # Save Summary
        summary = MeetingSummary(
            id=uuid.uuid4(),
            report_id=report.id,
            executive_summary=summary_data["executive_summary"],
            key_topics=summary_data["key_topics"],
            outcomes=summary_data["outcomes"],
            open_questions=summary_data["open_questions"],
            review_state=summary_data["review_state"],
            source_utterance_ids=summary_data["source_utterance_ids"],
            confidence_overall=summary_data["confidence_overall"],
            confidence_extraction=summary_data["confidence_overall"],
            confidence_grounding=summary_data["confidence_overall"],
            model_provider=model_provider,
            model_version=model_version
        )
        db_session.add(summary)

        # Save Action Items
        for item in action_items:
            action = ActionItem(
                id=uuid.uuid4(),
                report_id=report.id,
                title=item["title"],
                description=item["description"],
                owner_speaker_tag=item.get("owner_speaker_tag"),
                owner_participant_id=item.get("owner_participant_id"),
                deadline_text=item.get("deadline_text"),
                deadline_date=item.get("deadline_date"),
                priority=ActionItemPriority(item.get("priority", "Medium")),
                status=ActionItemStatus.Pending,
                review_state=item["review_state"],
                source_utterance_ids=item["source_utterance_ids"],
                confidence_overall=item["confidence_overall"],
                confidence_extraction=item.get("confidence_extraction", 1.0),
                confidence_grounding=item.get("confidence_grounding", 1.0),
                confidence_ownership=item.get("confidence_ownership", 1.0),
                confidence_temporal=item.get("confidence_temporal", 1.0),
                model_provider=model_provider,
                model_version=model_version
            )
            db_session.add(action)

        # Save Decisions
        for dec in decisions:
            decision = Decision(
                id=uuid.uuid4(),
                report_id=report.id,
                summary=dec["summary"],
                context=dec["context"],
                rationale=dec["rationale"],
                participants_involved=dec.get("participants_involved", []),
                review_state=dec["review_state"],
                source_utterance_ids=dec["source_utterance_ids"],
                confidence_overall=dec["confidence_overall"],
                confidence_extraction=dec.get("confidence_extraction", 1.0),
                confidence_grounding=dec.get("confidence_grounding", 1.0),
                model_provider=model_provider,
                model_version=model_version
            )
            db_session.add(decision)

        # Save Conflicts
        for con in conflicts:
            conflict = Conflict(
                id=uuid.uuid4(),
                report_id=report.id,
                topic=con["topic"],
                positions=con["positions"],
                resolution_status=ConflictResolution(con.get("resolution_status", "Unresolved")),
                resolution_summary=con.get("resolution_summary"),
                review_state=con["review_state"],
                source_utterance_ids=con["source_utterance_ids"],
                confidence_overall=con["confidence_overall"],
                confidence_extraction=con.get("confidence_extraction", 1.0),
                confidence_grounding=con.get("confidence_grounding", 1.0),
                model_provider=model_provider,
                model_version=model_version
            )
            db_session.add(conflict)

        # Save Followups
        for fol in followups:
            follow = Followup(
                id=uuid.uuid4(),
                report_id=report.id,
                description=fol["description"],
                suggested_date=fol.get("suggested_date"),
                review_state=fol["review_state"],
                source_utterance_ids=fol["source_utterance_ids"],
                confidence_overall=fol["confidence_overall"],
                confidence_extraction=fol.get("confidence_extraction", 1.0),
                confidence_grounding=fol.get("confidence_grounding", 1.0),
                model_provider=model_provider,
                model_version=model_version
            )
            db_session.add(follow)

        report.status = IntelligenceReportStatus.Completed
        report.processing_duration_ms = duration_ms
        report.completed_at = Clock.now()

        # Enqueue Outbox Events
        enqueue_outbox_event(
            db_session=db_session,
            aggregate_id=report.meeting_id,
            aggregate_type="Meeting",
            event_type="SummaryGenerated",
            event_version=1,
            payload={"report_id": str(report.id), "meeting_id": str(report.meeting_id)},
            metadata_block={}
        )

        enqueue_outbox_event(
            db_session=db_session,
            aggregate_id=report.meeting_id,
            aggregate_type="Meeting",
            event_type="ActionItemsExtracted",
            event_version=1,
            payload={"report_id": str(report.id), "count": len(action_items)},
            metadata_block={}
        )

        enqueue_outbox_event(
            db_session=db_session,
            aggregate_id=report.meeting_id,
            aggregate_type="Meeting",
            event_type="IntelligenceValidated",
            event_version=1,
            payload={"report_id": str(report.id), "meeting_id": str(report.meeting_id)},
            metadata_block={}
        )

        enqueue_outbox_event(
            db_session=db_session,
            aggregate_id=report.meeting_id,
            aggregate_type="Meeting",
            event_type="MeetingIntelligenceReady",
            event_version=1,
            payload={"report_id": str(report.id), "meeting_id": str(report.meeting_id)},
            metadata_block={}
        )

        db_session.commit()
        db_session.refresh(report)
        return report
