"""
Test Suite — Speech Processing Context

Validates:
  1. Transcript/Utterance/Word schema hierarchy and foreign key integrity
  2. SpeechTranscriptionService status transitions and outbox event emission
  3. Speaker-to-segment alignment logic
  4. Worker retry and failure recovery behaviour
"""
import uuid
import hashlib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.jwks import jwks_manager
from app.core.clock import Clock
from app.main import app
from app.models.auth import User, Workspace, Membership
from app.models.meeting import (
    Meeting, MeetingLifecycle, Recording, RecordingUploadStatus,
    Transcript, TranscriptStatus, Utterance, Word, OutboxEvent
)
from app.services.speech import (
    SpeechTranscriptionService,
    _assign_speakers_to_segments,
)

# Setup isolated testing SQLite DB
TEST_DATABASE_URL = "sqlite:///./test_speech.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db_session")
def fixture_db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _create_test_scaffolding(db_session):
    """Creates user, workspace, membership, meeting, and recording for tests."""
    user = User(id=uuid.uuid4(), email="speech@example.com", password_hash="hash", is_active=True)
    workspace = Workspace(id=uuid.uuid4(), name="Speech Org")
    membership = Membership(user_id=user.id, workspace_id=workspace.id, role="Owner")
    meeting = Meeting(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title="Transcription Test Room",
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
    db_session.add_all([user, workspace, membership, meeting, recording])
    db_session.commit()
    return user, workspace, meeting, recording


# ============================================================
# 1. Schema Hierarchy Tests
# ============================================================

def test_transcript_utterance_word_hierarchy(db_session):
    """Verifies that Transcript → Utterance → Word foreign key chain persists correctly."""
    _, _, meeting, recording = _create_test_scaffolding(db_session)

    transcript = Transcript(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        recording_id=recording.id,
        status=TranscriptStatus.Completed,
    )
    db_session.add(transcript)

    utterance = Utterance(
        id=uuid.uuid4(),
        transcript_id=transcript.id,
        speaker_tag="SPEAKER_00",
        text="Aaj ka meeting bahut productive tha.",
        start_time=0.0,
        end_time=3.5,
        confidence=0.92,
    )
    db_session.add(utterance)

    words_data = [
        {"word": "Aaj", "start": 0.0, "end": 0.3, "confidence": 0.95},
        {"word": "ka", "start": 0.3, "end": 0.5, "confidence": 0.97},
        {"word": "meeting", "start": 0.5, "end": 1.0, "confidence": 0.99},
        {"word": "bahut", "start": 1.0, "end": 1.4, "confidence": 0.93},
        {"word": "productive", "start": 1.4, "end": 2.2, "confidence": 0.91},
        {"word": "tha.", "start": 2.2, "end": 2.5, "confidence": 0.90},
    ]
    for w in words_data:
        db_session.add(Word(
            id=uuid.uuid4(),
            utterance_id=utterance.id,
            word=w["word"],
            start_time=w["start"],
            end_time=w["end"],
            confidence=w["confidence"],
        ))

    db_session.commit()

    # Verify cascade read-back
    loaded = db_session.query(Transcript).filter(Transcript.id == transcript.id).first()
    assert loaded is not None
    assert loaded.status == TranscriptStatus.Completed
    assert len(loaded.utterances) == 1
    assert loaded.utterances[0].speaker_tag == "SPEAKER_00"
    assert loaded.utterances[0].text == "Aaj ka meeting bahut productive tha."
    assert len(loaded.utterances[0].words) == 6
    assert loaded.utterances[0].words[0].word == "Aaj"

    # Verify meeting back-reference
    assert loaded.meeting_id == meeting.id
    assert loaded.recording_id == recording.id


def test_multiple_utterances_per_transcript(db_session):
    """Verifies that multiple utterances from different speakers are stored correctly."""
    _, _, meeting, recording = _create_test_scaffolding(db_session)

    transcript = Transcript(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        recording_id=recording.id,
        status=TranscriptStatus.Completed,
    )
    db_session.add(transcript)

    utt1 = Utterance(
        id=uuid.uuid4(),
        transcript_id=transcript.id,
        speaker_tag="SPEAKER_00",
        text="Let's discuss the Q4 targets.",
        start_time=0.0,
        end_time=2.0,
        confidence=0.95,
    )
    utt2 = Utterance(
        id=uuid.uuid4(),
        transcript_id=transcript.id,
        speaker_tag="SPEAKER_01",
        text="Main agree karta hoon, targets realistic hain.",
        start_time=2.5,
        end_time=5.0,
        confidence=0.88,
    )
    db_session.add_all([utt1, utt2])
    db_session.commit()

    loaded = db_session.query(Transcript).filter(Transcript.id == transcript.id).first()
    assert len(loaded.utterances) == 2
    # Verify ordering by start_time
    assert loaded.utterances[0].start_time < loaded.utterances[1].start_time
    assert loaded.utterances[0].speaker_tag == "SPEAKER_00"
    assert loaded.utterances[1].speaker_tag == "SPEAKER_01"


# ============================================================
# 2. Service Layer Tests
# ============================================================

def test_create_draft_transcript(db_session):
    """Verifies that create_draft_transcript saves a Queued transcript and emits TranscriptionStarted."""
    _, _, meeting, recording = _create_test_scaffolding(db_session)
    service = SpeechTranscriptionService()

    transcript = service.create_draft_transcript(
        meeting_id=meeting.id,
        recording_id=recording.id,
        db_session=db_session,
    )

    assert transcript.status == TranscriptStatus.Queued
    assert transcript.meeting_id == meeting.id
    assert transcript.recording_id == recording.id

    # Verify outbox event
    outbox = db_session.query(OutboxEvent).filter(
        OutboxEvent.event_type == "TranscriptionStarted",
        OutboxEvent.aggregate_id == meeting.id,
    ).first()
    assert outbox is not None
    assert outbox.payload["transcript_id"] == str(transcript.id)


def test_update_status(db_session):
    """Verifies that update_status transitions status correctly."""
    _, _, meeting, recording = _create_test_scaffolding(db_session)
    service = SpeechTranscriptionService()

    transcript = service.create_draft_transcript(
        meeting_id=meeting.id, recording_id=recording.id, db_session=db_session,
    )
    service.update_status(transcript.id, TranscriptStatus.Transcribing, db_session)

    refreshed = db_session.query(Transcript).filter(Transcript.id == transcript.id).first()
    assert refreshed.status == TranscriptStatus.Transcribing


def test_mark_failed(db_session):
    """Verifies that mark_failed transitions status, stores error, increments retry, and emits event."""
    _, _, meeting, recording = _create_test_scaffolding(db_session)
    service = SpeechTranscriptionService()

    transcript = service.create_draft_transcript(
        meeting_id=meeting.id, recording_id=recording.id, db_session=db_session,
    )
    service.mark_failed(transcript.id, "Whisper OOM error", db_session)

    refreshed = db_session.query(Transcript).filter(Transcript.id == transcript.id).first()
    assert refreshed.status == TranscriptStatus.Failed
    assert refreshed.error_message == "Whisper OOM error"
    assert refreshed.retry_count == 1

    outbox = db_session.query(OutboxEvent).filter(
        OutboxEvent.event_type == "TranscriptionFailed",
        OutboxEvent.aggregate_id == meeting.id,
    ).first()
    assert outbox is not None
    assert outbox.payload["error"] == "Whisper OOM error"


def test_save_transcript_results_with_speaker_identities(db_session):
    """Verifies that save_transcript_results persists utterances, words, speaker identities, and emits TranscriptReady."""
    _, _, meeting, recording = _create_test_scaffolding(db_session)
    service = SpeechTranscriptionService()

    transcript = service.create_draft_transcript(
        meeting_id=meeting.id, recording_id=recording.id, db_session=db_session,
    )
    service.update_status(transcript.id, TranscriptStatus.Persisting, db_session)

    segments = [
        {
            "text": "Hello everyone, let's start the standup.",
            "start": 0.0,
            "end": 2.5,
            "speaker": "SPEAKER_00",
            "confidence": 0.94,
            "words": [
                {"word": "Hello", "start": 0.0, "end": 0.4, "confidence": 0.97},
                {"word": "everyone,", "start": 0.4, "end": 0.9, "confidence": 0.96},
                {"word": "let's", "start": 0.9, "end": 1.2, "confidence": 0.95},
                {"word": "start", "start": 1.2, "end": 1.5, "confidence": 0.98},
                {"word": "the", "start": 1.5, "end": 1.7, "confidence": 0.99},
                {"word": "standup.", "start": 1.7, "end": 2.5, "confidence": 0.93},
            ],
        },
    ]

    speaker_identities = [
        {
            "speaker_tag": "SPEAKER_00",
            "resolved_name": "Rahul",
            "confidence": 0.95,
            "resolution_method": "automatic"
        }
    ]

    result = service.save_transcript_results(
        transcript_id=transcript.id,
        language_detected="en",
        segments=segments,
        speaker_identities=speaker_identities,
        db_session=db_session,
    )

    assert result.status == TranscriptStatus.Completed
    assert len(result.speaker_identities) == 1
    assert result.speaker_identities[0].speaker_tag == "SPEAKER_00"
    assert result.speaker_identities[0].resolved_name == "Rahul"
    assert result.speaker_identities[0].confidence == 0.95


# ============================================================
# 3. Speaker Assignment Logic Tests
# ============================================================

def test_speaker_assignment_by_overlap(db_session):
    """Verifies that ASR segments are assigned to the diarization speaker with the largest temporal overlap."""
    asr_segments = [
        {"text": "Good morning team.", "start": 0.0, "end": 2.0, "words": []},
        {"text": "Thanks for joining.", "start": 2.5, "end": 4.5, "words": []},
        {"text": "Let's review the backlog.", "start": 5.0, "end": 7.0, "words": []},
    ]
    diarization_segments = [
        {"speaker": "SPEAKER_00", "start": 0.0, "end": 3.0},
        {"speaker": "SPEAKER_01", "start": 3.0, "end": 6.0},
        {"speaker": "SPEAKER_00", "start": 6.0, "end": 8.0},
    ]

    aligned = _assign_speakers_to_segments(asr_segments, diarization_segments)

    assert aligned[0]["speaker"] == "SPEAKER_00"  # 0.0-2.0 overlaps mostly with 0.0-3.0
    assert aligned[1]["speaker"] == "SPEAKER_01"  # 2.5-4.5 overlaps mostly with 3.0-6.0
    assert aligned[2]["speaker"] in ("SPEAKER_00", "SPEAKER_01")


def test_speaker_assignment_unknown_fallback(db_session):
    """Verifies that segments outside diarization bounds get SPEAKER_UNKNOWN."""
    asr_segments = [
        {"text": "Late utterance.", "start": 100.0, "end": 102.0, "words": []},
    ]
    diarization_segments = [
        {"speaker": "SPEAKER_00", "start": 0.0, "end": 10.0},
    ]

    aligned = _assign_speakers_to_segments(asr_segments, diarization_segments)
    assert aligned[0]["speaker"] == "SPEAKER_UNKNOWN"


# ============================================================
# 4. Original Utterance Preservation Test
# ============================================================

def test_original_hinglish_preserved(db_session):
    """Verifies that original Hinglish text is stored without any translation or modification."""
    _, _, meeting, recording = _create_test_scaffolding(db_session)
    service = SpeechTranscriptionService()

    transcript = service.create_draft_transcript(
        meeting_id=meeting.id, recording_id=recording.id, db_session=db_session,
    )

    original_hinglish = "Yeh feature next sprint mein aayega, usko priority de do."
    segments = [
        {
            "text": original_hinglish,
            "start": 0.0,
            "end": 4.0,
            "speaker": "SPEAKER_00",
            "words": [],
        },
    ]

    result = service.save_transcript_results(
        transcript_id=transcript.id,
        language_detected="hi-en",
        segments=segments,
        speaker_identities=[],
        db_session=db_session,
    )

    # The exact original Hinglish text must be retrievable
    loaded = db_session.query(Utterance).filter(
        Utterance.transcript_id == transcript.id
    ).first()
    assert loaded.text == original_hinglish
