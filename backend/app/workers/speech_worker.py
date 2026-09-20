"""
Speech Processing Worker

Background worker that consumes RecordingVerified outbox events, downloads
audio from object storage, runs ASR and diarization pipelines, and persists
structured transcripts through the SpeechTranscriptionService.

The worker is model-agnostic: ASR and diarization engines are injected as
abstractions, allowing substitution of Whisper/Pyannote with mocks in tests
or alternative models in production.
"""
import uuid
import json
import logging
import asyncio
import tempfile
import os
from typing import Optional

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select

from app.core.config import settings
from app.core.clock import Clock
from app.models.meeting import (
    OutboxEvent, Recording, TranscriptStatus, Transcript
)
from app.services.speech import (
    ASREngine,
    DiarizationEngine,
    SpeechTranscriptionService,
    _assign_speakers_to_segments,
)
from app.infrastructure.storage import ObjectStorageService, MinIOStorageService
from app.infrastructure.events import enqueue_outbox_event

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [10, 60, 300]  # Exponential backoff in seconds


class SpeechProcessingWorker:
    """Stateless worker that processes RecordingVerified events.

    Lifecycle:
        1. Poll outbox for DELIVERED RecordingVerified events
        2. Download audio from S3
        3. Run diarization pipeline
        4. Run ASR pipeline
        5. Assign speakers to ASR segments
        6. Persist transcript hierarchy
        7. Emit TranscriptReady event
    """

    def __init__(
        self,
        db_session_factory: sessionmaker,
        asr_engine: ASREngine,
        diarization_engine: DiarizationEngine,
        storage: Optional[ObjectStorageService] = None,
        speech_service: Optional[SpeechTranscriptionService] = None,
    ):
        self.db_session_factory = db_session_factory
        self.asr_engine = asr_engine
        self.diarization_engine = diarization_engine
        self.storage = storage or MinIOStorageService()
        self.speech_service = speech_service or SpeechTranscriptionService()
        self.is_running = False

    async def start(self, poll_interval: float = 2.0) -> None:
        """Starts the event consumption loop."""
        self.is_running = True
        logger.info("Speech Processing Worker started.")

        while self.is_running:
            try:
                processed = await self.poll_and_process()
                if not processed:
                    await asyncio.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Worker cycle error: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)

    async def stop(self) -> None:
        self.is_running = False
        logger.info("Speech Processing Worker stopped.")

    async def poll_and_process(self) -> bool:
        """Scans outbox for RecordingVerified events and processes them."""
        with self.db_session_factory() as session:
            # Find DELIVERED RecordingVerified events that haven't been consumed
            # by the speech worker yet (no corresponding transcript exists)
            query = select(OutboxEvent).where(
                OutboxEvent.event_type == "RecordingVerified",
                OutboxEvent.status == "DELIVERED",
            ).limit(1)

            result = session.execute(query)
            event = result.scalar_one_or_none()

            if not event:
                return False

            meeting_id = uuid.UUID(event.payload["meeting_id"])
            recording_id = uuid.UUID(event.payload["recording_id"])
            
            # Restore trace context if present in event metadata
            from app.core.tracing import TraceContextManager
            trace_id = event.metadata_block.get("trace_id")
            parent_span_id = event.metadata_block.get("span_id")
            if trace_id:
                # Generate worker span
                TraceContextManager.set_trace_context(trace_id, str(uuid.uuid4()), parent_span_id)

            # Check if a transcript already exists for this recording
            existing = session.query(Transcript).filter(
                Transcript.recording_id == recording_id
            ).first()

            if existing:
                # Already processed — mark event as consumed
                event.status = "CONSUMED"
                session.commit()
                TraceContextManager.clear_trace_context()
                return True

        # Process the recording through the speech pipeline
        import time
        from app.core.metrics import metrics_collector
        start_time = time.time()
        
        try:
            await self.process_recording(meeting_id, recording_id)
            duration_ms = (time.time() - start_time) * 1000
            metrics_collector.record_duration("transcription_duration_ms", duration_ms)
        finally:
            TraceContextManager.clear_trace_context()
            
        return True

    async def process_recording(
        self,
        meeting_id: uuid.UUID,
        recording_id: uuid.UUID,
    ) -> None:
        """Full pipeline: download → diarize → transcribe → align → persist."""
        with self.db_session_factory() as session:
            # Re-bind trace inside db transaction block if needed
            from app.core.tracing import TraceContextManager
            
            # 1. Create draft transcript
            transcript = self.speech_service.create_draft_transcript(
                meeting_id=meeting_id,
                recording_id=recording_id,
                db_session=session,
            )
            transcript_id = transcript.id

            # Load recording metadata
            recording = session.query(Recording).filter(Recording.id == recording_id).first()
            if not recording:
                self.speech_service.mark_failed(
                    transcript_id, "Recording not found", session
                )
                return

            s3_bucket = recording.s3_bucket
            s3_key = recording.s3_key
            language_hint = recording.language_hint

        # 2. Download audio to temporary file
        tmp_path = None
        try:
            with self.db_session_factory() as session:
                self.speech_service.update_status(transcript_id, TranscriptStatus.Downloading, session)

            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            os.close(tmp_fd)

            audio_data = await self.storage.download_object(s3_bucket, s3_key)
            with open(tmp_path, "wb") as f:
                f.write(audio_data)

            # 3. Run diarization / 4. Run ASR
            with self.db_session_factory() as session:
                self.speech_service.update_status(transcript_id, TranscriptStatus.Transcribing, session)

            logger.info(f"Starting diarization for transcript {transcript_id}")
            diarization_segments = self.diarization_engine.diarize(tmp_path)
            logger.info(f"Diarization complete: {len(diarization_segments)} speaker segments")

            logger.info(f"Starting ASR for transcript {transcript_id}")
            asr_result = self.asr_engine.transcribe(tmp_path, language_hint=language_hint)
            logger.info(f"ASR complete: {len(asr_result['segments'])} segments, language={asr_result['language']}")

            # 5. Assign speakers to ASR segments
            with self.db_session_factory() as session:
                self.speech_service.update_status(transcript_id, TranscriptStatus.Aligning, session)

            aligned_segments = _assign_speakers_to_segments(
                asr_result["segments"],
                diarization_segments,
            )

            # Extract speaker tags for resolution mapping
            unique_speakers = list(set(seg.get("speaker", "SPEAKER_UNKNOWN") for seg in aligned_segments))
            speaker_identities = []
            for tag in unique_speakers:
                speaker_identities.append({
                    "speaker_tag": tag,
                    "resolved_name": f"Resolved {tag}",
                    "confidence": 0.9,
                    "resolution_method": "automatic"
                })

            # 6. Persist results
            with self.db_session_factory() as session:
                self.speech_service.update_status(transcript_id, TranscriptStatus.Persisting, session)
                self.speech_service.save_transcript_results(
                    transcript_id=transcript_id,
                    language_detected=asr_result["language"],
                    segments=aligned_segments,
                    speaker_identities=speaker_identities,
                    db_session=session,
                )

            logger.info(f"Transcript {transcript_id} completed successfully.")

        except Exception as e:
            logger.error(f"Speech pipeline failed for transcript {transcript_id}: {e}", exc_info=True)

            with self.db_session_factory() as session:
                transcript = session.query(Transcript).filter(
                    Transcript.id == transcript_id
                ).first()

                if transcript and transcript.retry_count < MAX_RETRIES:
                    self.speech_service.mark_failed(
                        transcript_id, str(e), session
                    )
                    logger.warning(
                        f"Transcript {transcript_id} marked as Failed. "
                        f"Retry {transcript.retry_count + 1}/{MAX_RETRIES}"
                    )
                elif transcript:
                    transcript.status = TranscriptStatus.Failed
                    transcript.error_message = f"Max retries exceeded: {e}"
                    transcript.retry_count += 1

                    enqueue_outbox_event(
                        db_session=session,
                        aggregate_id=transcript.meeting_id,
                        aggregate_type="Meeting",
                        event_type="TranscriptionFailed",
                        event_version=1,
                        payload={
                            "meeting_id": str(transcript.meeting_id),
                            "transcript_id": str(transcript_id),
                            "error": str(e),
                            "retry_count": transcript.retry_count,
                            "dead_letter": True,
                        },
                        metadata_block={}
                    )
                    session.commit()
                    logger.error(f"Transcript {transcript_id} exhausted retries. Dead-lettered.")

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
