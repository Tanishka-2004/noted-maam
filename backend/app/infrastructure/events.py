import uuid
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import redis.asyncio as aioredis
from sqlalchemy import select, update, and_, or_
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.clock import Clock
from app.models.meeting import OutboxEvent

logger = logging.getLogger(__name__)

class EventDispatcher(ABC):
    @abstractmethod
    async def dispatch(
        self,
        event_uuid: uuid.UUID,
        aggregate_id: uuid.UUID,
        aggregate_type: str,
        event_type: str,
        event_version: int,
        payload: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> None:
        """Publishes the integration event to the message broker."""
        pass


class RedisEventDispatcher(EventDispatcher):
    def __init__(self):
        # Establish connection pool using REDIS_STREAM_URL
        self.redis_client = aioredis.from_url(settings.REDIS_STREAM_URL)

    async def dispatch(
        self,
        event_uuid: uuid.UUID,
        aggregate_id: uuid.UUID,
        aggregate_type: str,
        event_type: str,
        event_version: int,
        payload: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> None:
        # Wrap as v1 versioned event
        integration_event = {
            "event_uuid": str(event_uuid),
            "aggregate_id": str(aggregate_id),
            "aggregate_type": aggregate_type,
            "event_type": f"{event_type}.v{event_version}",
            "event_version": event_version,
            "payload": json.dumps(payload),
            "metadata": json.dumps(metadata),
            "occurred_at": Clock.now().isoformat()
        }

        # XADD to the stream named "meeting_events"
        await self.redis_client.xadd(
            name="meeting_events",
            fields=integration_event,
            id="*"
        )


from app.core.tracing import TraceContextManager

def enqueue_outbox_event(
    db_session: Any,
    aggregate_id: uuid.UUID,
    aggregate_type: str,
    event_type: str,
    event_version: int,
    payload: Dict[str, Any],
    metadata_block: Dict[str, Any]
) -> uuid.UUID:
    """Inserts a pending event to the outbox table within the current database transaction."""
    event_uuid = uuid.uuid4()
    now = Clock.now()

    # Capture tracing ContextVars
    trace_context = TraceContextManager.get_context_dict()
    updated_metadata = dict(metadata_block or {})
    if trace_context.get("trace_id"):
        updated_metadata["trace_id"] = trace_context["trace_id"]
        updated_metadata["span_id"] = trace_context["span_id"]
        updated_metadata["parent_span_id"] = trace_context["parent_span_id"]

    outbox_event = OutboxEvent(
        id=uuid.uuid4(),
        event_uuid=event_uuid,
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        event_type=event_type,
        event_version=event_version,
        payload=payload,
        metadata_block=updated_metadata,
        status="PENDING",
        retry_count=0,
        occurred_at=now
    )
    db_session.add(outbox_event)
    return event_uuid


class OutboxDispatcherService:
    def __init__(self, db_session_factory: sessionmaker, dispatcher: EventDispatcher):
        self.db_session_factory = db_session_factory
        self.dispatcher = dispatcher
        self.is_running = False

    async def start(self, poll_interval: float = 1.0) -> None:
        self.is_running = True
        logger.info("Outbox event dispatcher worker started.")
        while self.is_running:
            try:
                processed_count = await self.process_batch()
                if processed_count == 0:
                    await asyncio.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Error in outbox dispatcher cycle: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)

    async def stop(self) -> None:
        self.is_running = False
        logger.info("Outbox event dispatcher worker stopped.")

    async def process_batch(self, batch_size: int = 50) -> int:
        """Acquires a lease lock, dispatches, and updates statuses transactionally."""
        now = Clock.now()
        lease_duration = datetime_leeway = 10.0 # lease lock valid for 10 seconds

        with self.db_session_factory() as session:
            # Query PENDING or expired locked PROCESSING events
            # For SQLite compatibility, we handle time queries and update fields
            lease_expiry = now
            query = select(OutboxEvent).where(
                or_(
                    OutboxEvent.status == "PENDING",
                    and_(
                        OutboxEvent.status == "PROCESSING",
                        OutboxEvent.lease_locked_until < lease_expiry
                    )
                )
            ).limit(batch_size)

            result = session.execute(query)
            events = result.scalars().all()

            if not events:
                return 0

            # Acquire lease
            event_ids = [e.id for e in events]
            from datetime import timedelta
            locked_until = now + timedelta(seconds=lease_duration)

            stmt = update(OutboxEvent).where(OutboxEvent.id.in_(event_ids)).values(
                status="PROCESSING",
                lease_locked_until=locked_until
            )
            session.execute(stmt)
            session.commit()

        # Process each leased event individually
        processed_count = 0
        for event_id in event_ids:
            with self.db_session_factory() as session:
                # Reload event in current transaction context
                reload_stmt = select(OutboxEvent).where(OutboxEvent.id == event_id)
                res = session.execute(reload_stmt)
                db_event = res.scalar_one_or_none()

                if not db_event:
                    continue

                try:
                    await self.dispatcher.dispatch(
                        event_uuid=db_event.event_uuid,
                        aggregate_id=db_event.aggregate_id,
                        aggregate_type=db_event.aggregate_type,
                        event_type=db_event.event_type,
                        event_version=db_event.event_version,
                        payload=db_event.payload,
                        metadata=db_event.metadata_block
                    )
                    db_event.status = "DELIVERED"
                    db_event.published_at = Clock.now()
                    db_event.lease_locked_until = None
                except Exception as ex:
                    db_event.retry_count += 1
                    db_event.last_error = str(ex)
                    if db_event.retry_count >= 5:
                        db_event.status = "DEAD_LETTER"
                        logger.error(f"Event {db_event.event_uuid} reached max retries. Moved to DEAD_LETTER.")
                    else:
                        db_event.status = "PENDING"  # Release lease
                    db_event.lease_locked_until = None

                session.commit()
                processed_count += 1

        return processed_count
