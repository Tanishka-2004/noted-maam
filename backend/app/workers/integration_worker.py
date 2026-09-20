"""
External Integrations Background Worker

Consumes MeetingIntelligenceReady events, resolves active tenant integrations configs,
enqueues tracking records, and executes outbound dispatches with trace context propagation
and retry failure classification rules.
"""
import uuid
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select

from app.core.clock import Clock
from app.models.meeting import (
    OutboxEvent, IntegrationConfig, IntegrationOutbox,
    Meeting, IntelligenceReport, MeetingSummary, ActionItem, Decision, Conflict, Followup
)
from app.services.integrations import IntegrationRouterService
from app.core.tracing import TraceContextManager
from app.core.metrics import metrics_collector

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


class IntegrationWorker:
    """Consumes internal intelligence events, routing outbound dispatches safely."""

    def __init__(
        self,
        db_session_factory: sessionmaker,
        router_service: Optional[IntegrationRouterService] = None
    ):
        self.db_session_factory = db_session_factory
        self.router = router_service or IntegrationRouterService()
        self.is_running = False

    async def start(self, poll_interval: float = 2.0) -> None:
        self.is_running = True
        logger.info("External Integrations Worker started.")
        while self.is_running:
            try:
                processed = await self.poll_and_process_inbound()
                processed_outbound = await self.poll_and_process_outbound()
                if not processed and not processed_outbound:
                    await asyncio.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Integrations worker loop error: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)

    async def stop(self) -> None:
        self.is_running = False
        logger.info("External Integrations Worker stopped.")

    async def poll_and_process_inbound(self) -> bool:
        """Polls for new MeetingIntelligenceReady outbox events and enqueues IntegrationOutbox jobs."""
        with self.db_session_factory() as session:
            query = select(OutboxEvent).where(
                OutboxEvent.event_type == "MeetingIntelligenceReady",
                OutboxEvent.status == "DELIVERED"
            ).limit(1)
            result = session.execute(query)
            event = result.scalar_one_or_none()

            if not event:
                return False

            meeting_id = uuid.UUID(event.payload["meeting_id"])
            report_id = uuid.UUID(event.payload["report_id"])

            # Resolve active configs for the meeting's workspace
            meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting:
                event.status = "CONSUMED"
                session.commit()
                return True

            configs = session.query(IntegrationConfig).filter(
                IntegrationConfig.workspace_id == meeting.workspace_id,
                IntegrationConfig.is_active == True
            ).all()

            if not configs:
                # No active configs to route to, mark event consumed
                event.status = "CONSUMED"
                session.commit()
                return True

            # Compile consolidated intelligence payload to distribute
            summaries = session.query(MeetingSummary).filter(MeetingSummary.report_id == report_id).all()
            actions = session.query(ActionItem).filter(ActionItem.report_id == report_id).all()
            decisions = session.query(Decision).filter(Decision.report_id == report_id).all()

            payload = {
                "meeting_id": str(meeting_id),
                "report_id": str(report_id),
                "summary": summaries[0].executive_summary if summaries else "",
                "action_items": [{"title": a.title, "priority": a.priority} for a in actions],
                "decisions": [d.summary for d in decisions]
            }

            # Enqueue tracking jobs idempotently
            for config in configs:
                idem_key = f"{meeting_id}:{report_id}:{config.provider}"
                
                # Check duplicate
                dup = session.query(IntegrationOutbox).filter(
                    IntegrationOutbox.idempotency_key == idem_key
                ).first()

                if not dup:
                    job = IntegrationOutbox(
                        id=uuid.uuid4(),
                        workspace_id=meeting.workspace_id,
                        integration_id=config.id,
                        idempotency_key=idem_key,
                        status="Queued",
                        payload=payload,
                        trace_id=event.metadata_block.get("trace_id")
                    )
                    session.add(job)

            event.status = "CONSUMED"
            session.commit()
            return True

    async def poll_and_process_outbound(self) -> bool:
        """Polls IntegrationOutbox for Queued or Retrying tasks and executes dispatches."""
        with self.db_session_factory() as session:
            # Query Queued or expired Retrying tasks
            query = select(IntegrationOutbox).where(
                IntegrationOutbox.status.in_(["Queued", "Retrying"])
            ).limit(1)
            result = session.execute(query)
            job = result.scalar_one_or_none()

            if not job:
                return False

            # Set trace context
            if job.trace_id:
                TraceContextManager.set_trace_context(job.trace_id, str(uuid.uuid4()))

            job.status = "Dispatching"
            session.commit()

            # Load configuration
            config = session.query(IntegrationConfig).filter(
                IntegrationConfig.id == job.integration_id
            ).first()

            if not config or not config.is_active:
                job.status = "Cancelled"
                job.failure_reason = "Integration configuration disabled or removed"
                session.commit()
                TraceContextManager.clear_trace_context()
                return True

            job_id = job.id
            payload = job.payload

        # Execute dispatch
        import time
        start_time = time.time()
        metrics_collector.increment("integration_requests_total", 1.0, {"provider": config.provider})

        try:
            res = await self.router.route_dispatch(config, payload)
            
            with self.db_session_factory() as session:
                active_job = session.query(IntegrationOutbox).filter(IntegrationOutbox.id == job_id).first()
                active_job.status = "Delivered"
                active_job.last_attempt_at = Clock.now()
                active_job.attempt_count += 1
                active_job.http_status = res.get("http_status")
                session.commit()

            duration_ms = (time.time() - start_time) * 1000
            metrics_collector.record_duration("integration_latency_ms", duration_ms, {"provider": config.provider})
            metrics_collector.increment("integration_success_total", 1.0, {"provider": config.provider})

        except Exception as e:
            # Classify failure retry status
            is_retryable = self._classify_error(e)
            
            with self.db_session_factory() as session:
                active_job = session.query(IntegrationOutbox).filter(IntegrationOutbox.id == job_id).first()
                active_job.attempt_count += 1
                active_job.last_attempt_at = Clock.now()
                active_job.failure_reason = str(e)

                # Fetch HTTP status if from network client
                if hasattr(e, "response") and e.response:
                    active_job.http_status = e.response.status_code

                if is_retryable and active_job.attempt_count < MAX_RETRIES:
                    active_job.status = "Retrying"
                    metrics_collector.increment("integration_retry_total", 1.0, {"provider": config.provider})
                else:
                    active_job.status = "DeadLetter"
                    metrics_collector.increment("integration_dlq_total", 1.0, {"provider": config.provider})
                    metrics_collector.increment("integration_failure_total", 1.0, {"provider": config.provider})

                session.commit()

        finally:
            TraceContextManager.clear_trace_context()

        return True

    def _classify_error(self, e: Exception) -> bool:
        """Determines if the exception represents a temporary network/rate issue or permanent client error."""
        # Check HTTP exceptions status codes
        if hasattr(e, "response") and e.response is not None:
            code = e.response.status_code
            # Permanent errors: 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found
            if code in [400, 401, 403, 404]:
                return False
            # Retryable: 429 Rate limits, 5xx Server errors
            if code == 429 or code >= 500:
                return True

        # Timeout or basic network errors are retryable
        import httpx
        if isinstance(e, (asyncio.TimeoutError, httpx.RequestError)):
            return True

        # General runtime exceptions (e.g. template issues, validation failures) are non-retryable
        return False
