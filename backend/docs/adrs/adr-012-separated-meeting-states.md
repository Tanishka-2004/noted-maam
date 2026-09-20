# ADR-012: Separation of Meeting Lifecycle, Recording Status, and AI Processing States

**Status:** Accepted  
**Date:** 2026-07-10  
**Deciders:** Platform Engineering & Systems Architecture  

---

## Context

A meeting in the Noted Ma'am system involves multiple concurrent concerns:
1. **Meeting Lifecycle**: The client-facing status of the meeting room (e.g. Scheduled, Waiting, Recording, Ended, Archived).
2. **Recording Status**: The upload and integrity state of the audio files (e.g. Waiting, Uploading, Uploaded, Verified, Deleted).
3. **AI Processing Lifecycle**: The progress of transcription, summarization, entity extraction, and vector indexing (e.g. Pending, Queued, Transcribing, Extracting, Indexing, Completed, Failed).

If modeled as a single state variable, the system faces state explosion, complex state validation rules, and direct coupling of user actions with background workers.

---

## Decision

We will explicitly model **three separate state concerns** as distinct columns on the `Meeting` and `Recording` entities, each managed by independent state machine rules:

### 1. Meeting Lifecycle (Stored in `meetings.lifecycle_state`)
Governs user-facing meeting operations. State changes are initiated exclusively by authenticated participants:
- `Scheduled`: Room planned for the future.
- `Waiting`: Room is active, waiting for participants/recording to start.
- `Recording`: Audio capture is active.
- `Ended`: Meeting has concluded, room is closed.
- `Archived`: Meeting is read-only.

### 2. Recording Status (Stored in `recordings.upload_status`)
Tracks physical media ingestion states:
- `Waiting`: Expecting client stream/payload connection.
- `Uploading`: Audio chunks are actively streaming to MinIO/S3.
- `Uploaded`: Streaming completes, file is locked.
- `Verified`: Media checksum matching validation and codec verification passes.
- `Deleted`: Media files are purged due to retention rules.

### 3. AI Processing Lifecycle (Stored in `meetings.processing_status`)
Tracks progress of asynchronous AI engines:
- `Pending`: No audio files submitted yet.
- `Queued`: Audio uploaded and verified, queued for worker threads.
- `Transcribing`: ASR engines actively transcribing Hinglish streams.
- `Extracting`: NER and summary generators extracting actions and conflicts.
- `Indexing`: Generating and writing semantic search embeddings.
- `Completed`: All AI tasks completed successfully.
- `Failed`: An AI component timed out or threw an exception.

---

## State Transition Diagrams

```
Meeting Room Lifecycle:
[ Scheduled ] ──► [ Waiting ] ──► [ Recording ] ──► [ Ended ] ──► [ Archived ]

Recording Status:
[ Waiting ] ──► [ Uploading ] ──► [ Uploaded ] ──► [ Verified ] ──► [ Deleted ]

AI Processing Status:
[ Pending ] ──► [ Queued ] ──► [ Transcribing ] ──► [ Extracting ] ──► [ Indexing ] ──► [ Completed ]
                                                                                   └──► [ Failed ]
```

---

## Consequences

- **Positive:** Clarifies state updates: clients can view if a meeting has ended even if the ASR transcription is still processing or failed.
- **Positive:** Background processing crashes (e.g., transcription API timeouts) do not lock the meeting room status or block archive actions.
- **Negative:** Increased database column footprints.
- **Complexity:** Requires coordinate checks (e.g. the system must assert a meeting is `Ended` before AI processing finalizes index structures, and block uploads if a recording is `Deleted`).
