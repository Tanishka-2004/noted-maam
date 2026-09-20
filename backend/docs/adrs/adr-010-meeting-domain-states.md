# ADR-010: Separation of Meeting Lifecycle and AI Processing States

**Status:** Accepted  
**Date:** 2026-07-10  
**Deciders:** Platform Engineering & Product Architecture  

---

## Context

A meeting exhibits two distinct lifecycles:
1. **Meeting Lifecycle**: The user-facing state of the meeting room (e.g. Scheduled, Waiting, Recording, Ended, Archived).
2. **AI Processing Lifecycle**: The system-facing state of the media files being transcribed, analyzed, and summarized (e.g. Pending, Uploading, Queued, Transcribing, Processing, Completed, Failed).

Combining these concerns into a single `MeetingState` enum leads to a state explosion, complicates transition validations, and creates tight coupling between meeting orchestration and background asynchronous AI pipelines.

---

## Decision

We will isolate the two state machines inside the `Meeting` aggregate model:

1. **Independent State Enums**:
   - `MeetingLifecycle`: `Scheduled` -> `Waiting` -> `Recording` -> `Ended` -> `Archived`.
   - `ProcessingStatus`: `Pending` -> `Uploading` -> `Queued` -> `Transcribing` -> `Processing` -> `Completed` / `Failed`.
2. **Aggregate Rule Enforcement**: All transitions are controlled strictly via domain methods on the `Meeting` model (e.g. `Meeting.start_recording()`, `Meeting.end_meeting()`), which assert preconditions and mutate state fields in tandem.
3. **Database Separation**:
   - Store these states in separate columns (`lifecycle_state` and `processing_status`) within the `meetings` database table.

---

## State Transition Rules

### Meeting Lifecycle Transitions
```
[ Scheduled ] ──► [ Waiting ] ──► [ Recording ] ──► [ Ended ] ──► [ Archived ]
```

- Spontaneous meetings can skip the `Scheduled` state, transitioning directly to `Recording`.
- Users can end a meeting from the `Waiting` or `Recording` state.
- Archived meetings are read-only.

### AI Processing Transitions
```
[ Pending ] ──► [ Uploading ] ──► [ Queued ] ──► [ Transcribing ] ──► [ Processing ] ──► [ Completed ]
                                                                                   └──► [ Failed ]
```

- Starts at `Pending` when the meeting is created.
- Transitions to `Uploading` when audio ingestion commences.
- Enters `Queued` once the audio checksum is verified and registered.
- Transcribing and Processing states are updated by background workers.

---

## Consequences

- **Positive:** Simpler transition rules and easier debugging of meeting lifecycle bugs vs transcript/AI pipeline bugs.
- **Positive:** The meeting scheduler and room controller remain functional even if downstream AI services (e.g. Whisper, LLM APIs) experience outages or failures.
- **Negative:** Increased schema complexity (two enum database columns instead of one).
- **Negative:** Frontend needs to consume and map two state variables to display the meeting state correctly to the user.
