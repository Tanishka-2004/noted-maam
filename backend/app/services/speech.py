"""
Speech Processing Service Layer

Manages Transcript aggregate lifecycle transitions, persists utterance and word
hierarchies, and emits domain events through the transactional outbox.

This service is consumed by the speech worker and does NOT contain any ASR or
diarization logic. It is model-agnostic.
"""
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models.meeting import (
    Transcript, TranscriptStatus, Utterance, Word, Recording, OutboxEvent, SpeakerIdentity
)
from app.infrastructure.events import enqueue_outbox_event

logger = logging.getLogger(__name__)


# ============================================================
# ASR & Diarization Engine Abstractions
# ============================================================

class ASREngine(ABC):
    """Abstract interface for Automatic Speech Recognition engines.

    Concrete implementations wrap model-specific inference (e.g. Whisper,
    faster-whisper). The Speech Processing Context is the only consumer.
    """

    @abstractmethod
    def transcribe(self, audio_path: str, language_hint: str = "auto") -> Dict[str, Any]:
        """Transcribes an audio file and returns structured segments.

        Returns:
            {
                "language": "en" | "hi" | "hi-en",
                "segments": [
                    {
                        "text": "the spoken words",
                        "start": 0.0,
                        "end": 2.5,
                        "words": [
                            {"word": "the", "start": 0.0, "end": 0.3, "confidence": 0.97},
                            ...
                        ]
                    },
                    ...
                ]
            }
        """
        pass


class DiarizationEngine(ABC):
    """Abstract interface for speaker diarization engines.

    Concrete implementations wrap model-specific clustering (e.g. Pyannote).
    """

    @abstractmethod
    def diarize(self, audio_path: str) -> List[Dict[str, Any]]:
        """Identifies speaker segments in an audio file.

        Returns:
            [
                {"speaker": "SPEAKER_00", "start": 0.0, "end": 5.2},
                {"speaker": "SPEAKER_01", "start": 5.2, "end": 12.8},
                ...
            ]
        """
        pass


class WhisperASREngine(ASREngine):
    """Wraps faster-whisper for multilingual (English/Hindi/Hinglish) ASR."""

    def __init__(self, model_size: str = "medium", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
            except ImportError:
                raise RuntimeError(
                    "faster-whisper is not installed. "
                    "Install it with: pip install faster-whisper"
                )
        return self._model

    def transcribe(self, audio_path: str, language_hint: str = "auto") -> Dict[str, Any]:
        model = self._load_model()

        language = None if language_hint == "auto" else language_hint
        segments_iter, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
        )

        segments = []
        for seg in segments_iter:
            words = []
            if seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "confidence": round(w.probability, 4) if hasattr(w, "probability") else 0.0,
                    })

            segments.append({
                "text": seg.text.strip(),
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "words": words,
            })

        return {
            "language": info.language,
            "segments": segments,
        }


class PyannoteDiarizationEngine(DiarizationEngine):
    """Wraps pyannote.audio for speaker diarization."""

    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token
        self._pipeline = None

    def _load_pipeline(self):
        if self._pipeline is None:
            try:
                from pyannote.audio import Pipeline
                self._pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=self.auth_token
                )
            except ImportError:
                raise RuntimeError(
                    "pyannote.audio is not installed. "
                    "Install it with: pip install pyannote.audio"
                )
        return self._pipeline

    def diarize(self, audio_path: str) -> List[Dict[str, Any]]:
        pipeline = self._load_pipeline()
        diarization = pipeline(audio_path)

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "speaker": speaker,
                "start": round(turn.start, 3),
                "end": round(turn.end, 3),
            })

        return segments


# ============================================================
# Speech Transcription Service
# ============================================================

def _assign_speakers_to_segments(
    asr_segments: List[Dict[str, Any]],
    diarization_segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Assigns speaker tags to ASR segments by finding the diarization segment
    with the largest temporal overlap for each ASR segment's midpoint."""

    for seg in asr_segments:
        midpoint = (seg["start"] + seg["end"]) / 2.0
        best_speaker = "SPEAKER_UNKNOWN"
        best_overlap = 0.0

        for d_seg in diarization_segments:
            overlap_start = max(seg["start"], d_seg["start"])
            overlap_end = min(seg["end"], d_seg["end"])
            overlap = max(0.0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = d_seg["speaker"]

        seg["speaker"] = best_speaker

    return asr_segments


class SpeechTranscriptionService:
    """Manages Transcript aggregate persistence and lifecycle events.

    This service does NOT invoke ASR or diarization models directly.
    It receives pre-processed results from the speech worker and persists them.
    """

    def create_draft_transcript(
        self,
        meeting_id: uuid.UUID,
        recording_id: uuid.UUID,
        db_session: Session
    ) -> Transcript:
        """Creates a Queued transcript record."""
        transcript = Transcript(
            id=uuid.uuid4(),
            meeting_id=meeting_id,
            recording_id=recording_id,
            status=TranscriptStatus.Queued,
        )
        db_session.add(transcript)

        enqueue_outbox_event(
            db_session=db_session,
            aggregate_id=meeting_id,
            aggregate_type="Meeting",
            event_type="TranscriptionStarted",
            event_version=1,
            payload={
                "meeting_id": str(meeting_id),
                "recording_id": str(recording_id),
                "transcript_id": str(transcript.id),
            },
            metadata_block={}
        )

        db_session.commit()
        return transcript

    def update_status(self, transcript_id: uuid.UUID, status: TranscriptStatus, db_session: Session) -> None:
        """Transitions transcript status to one of the granular statuses."""
        transcript = db_session.query(Transcript).filter(Transcript.id == transcript_id).first()
        if not transcript:
            raise ValueError(f"Transcript {transcript_id} not found")
        transcript.status = status
        db_session.commit()

    def mark_failed(
        self,
        transcript_id: uuid.UUID,
        error_message: str,
        db_session: Session
    ) -> None:
        """Transitions transcript status to Failed with an error message."""
        transcript = db_session.query(Transcript).filter(Transcript.id == transcript_id).first()
        if not transcript:
            raise ValueError(f"Transcript {transcript_id} not found")

        transcript.status = TranscriptStatus.Failed
        transcript.error_message = error_message
        transcript.retry_count += 1

        enqueue_outbox_event(
            db_session=db_session,
            aggregate_id=transcript.meeting_id,
            aggregate_type="Meeting",
            event_type="TranscriptionFailed",
            event_version=1,
            payload={
                "meeting_id": str(transcript.meeting_id),
                "transcript_id": str(transcript_id),
                "error": error_message,
                "retry_count": transcript.retry_count,
            },
            metadata_block={}
        )

        db_session.commit()

    def save_transcript_results(
        self,
        transcript_id: uuid.UUID,
        language_detected: str,
        segments: List[Dict[str, Any]],
        speaker_identities: List[Dict[str, Any]],
        db_session: Session
    ) -> Transcript:
        """Persists utterance and word hierarchies, maps speaker identities, marks Completed, and emits TranscriptReady.

        Args:
            segments: List of dicts with keys: text, start, end, speaker, words.
                      Each word dict has: word, start, end, confidence.
            speaker_identities: List of dicts with keys: speaker_tag, resolved_name, participant_id, confidence, resolution_method
        """
        transcript = db_session.query(Transcript).filter(Transcript.id == transcript_id).first()
        if not transcript:
            raise ValueError(f"Transcript {transcript_id} not found")

        transcript.language_detected = language_detected

        # Save Speaker Identities
        for identity in speaker_identities:
            spk_id = SpeakerIdentity(
                id=uuid.uuid4(),
                transcript_id=transcript.id,
                speaker_tag=identity["speaker_tag"],
                resolved_name=identity.get("resolved_name"),
                participant_id=identity.get("participant_id"),
                confidence=identity.get("confidence", 1.0),
                resolution_method=identity.get("resolution_method", "automatic")
            )
            db_session.add(spk_id)

        # Save Utterances & Words
        for seg in segments:
            utterance = Utterance(
                id=uuid.uuid4(),
                transcript_id=transcript.id,
                speaker_tag=seg.get("speaker", "SPEAKER_UNKNOWN"),
                text=seg["text"],
                start_time=seg["start"],
                end_time=seg["end"],
                confidence=seg.get("confidence", 0.0),
            )
            db_session.add(utterance)

            for w in seg.get("words", []):
                word_obj = Word(
                    id=uuid.uuid4(),
                    utterance_id=utterance.id,
                    word=w["word"],
                    start_time=w["start"],
                    end_time=w["end"],
                    confidence=w.get("confidence", 0.0),
                )
                db_session.add(word_obj)

        transcript.status = TranscriptStatus.Completed
        transcript.completed_at = Clock.now()

        enqueue_outbox_event(
            db_session=db_session,
            aggregate_id=transcript.meeting_id,
            aggregate_type="Meeting",
            event_type="TranscriptReady",
            event_version=1,
            payload={
                "meeting_id": str(transcript.meeting_id),
                "recording_id": str(transcript.recording_id),
                "transcript_id": str(transcript.id),
                "language": language_detected,
                "utterance_count": len(segments),
            },
            metadata_block={}
        )

        db_session.commit()
        db_session.refresh(transcript)
        return transcript
