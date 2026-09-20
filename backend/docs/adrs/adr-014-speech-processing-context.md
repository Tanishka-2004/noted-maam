# ADR-014: Speech Processing Bounded Context

**Status**: Accepted  
**Date**: 2026-07-10  
**Category**: Domain Architecture  
**Deciders**: Engineering Lead  

## Context

Following the completion of the Media Ingestion pipeline (Phase 4), the system needs to convert verified audio recordings into structured transcripts. This capability must support multilingual audio (English, Hindi, and Hinglish code-switching) while maintaining clean architectural boundaries.

The core question is whether speech processing should be embedded within the Meeting Domain or isolated as its own bounded context.

## Decision

We introduce a dedicated **Speech Processing Bounded Context** whose sole responsibility is producing structured transcripts from audio recordings.

### Boundaries

The Speech Processing Context:
- **Consumes**: `RecordingVerified` events from the Media Ingestion context
- **Produces**: `TranscriptReady` events consumed by downstream AI processing contexts
- **Does not know** about: action items, summaries, embeddings, semantic search, or any downstream intelligence

### Architecture

- **Transcript Aggregate**: `Transcript → Utterance → Word` hierarchy with speaker tags, timestamps, and confidence scores
- **Engine Abstractions**: `ASREngine` and `DiarizationEngine` abstract interfaces isolate model-specific logic (Whisper, Pyannote) from the service layer
- **Original Utterance Preservation**: Raw spoken text (including Hinglish) is stored permanently; translations are linked as optional dependent attributes
- **Background Worker**: Stateless worker consumes outbox events, downloads audio from S3, runs the speech pipeline, and persists results through the `SpeechTranscriptionService`

### Event Flow

```
RecordingVerified → TranscriptionStarted → TranscriptionCompleted/Failed → TranscriptReady
```

## Alternatives Considered

1. **Embed transcription in Meeting Domain**: Rejected because it violates single responsibility and couples AI model dependencies into the core domain.
2. **Direct API-triggered transcription**: Rejected because ASR is long-running and should execute asynchronously via background workers.
3. **Combined Speech + Intelligence context**: Rejected because summarization, NER, and embedding generation have fundamentally different lifecycle and scaling characteristics.

## Consequences

- Clean separation allows ASR models to be upgraded or swapped without affecting the Meeting or AI contexts
- Transcript schema provides a stable interface for downstream consumers
- Worker architecture supports horizontal scaling and retry/dead-letter patterns
- Original utterances are preserved for future model reprocessing

## Impacted Components

| Component | Impact |
| --- | --- |
| `app/models/meeting.py` | Added `Transcript`, `Utterance`, `Word` models |
| `app/services/speech.py` | New service layer with engine abstractions |
| `app/workers/speech_worker.py` | New background worker |
| `app/infrastructure/storage.py` | Added `download_object` method |
| `app/models/__init__.py` | Registered new model exports |
