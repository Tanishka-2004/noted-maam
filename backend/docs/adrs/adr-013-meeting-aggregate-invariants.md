# ADR-013: Meeting Aggregate Invariants & Domain Boundaries

**Status:** Accepted  
**Date:** 2026-07-10  
**Deciders:** Platform Engineering & Security Architecture  

---

## Context

In complex enterprise domain services, business validation rules can easily leak into HTTP routing controllers, REST APIs, or downstream background workers. This duplication leads to inconsistencies: for example, a background worker might transition a meeting room state without verifying if the meeting has already been archived or soft-deleted, corrupting the lifecycle state.

To enforce domain integrity, we require all business validations to reside inside the `Meeting` aggregate root.

---

## Decision

1. **Encapsulated Aggregate State Mutators**:
   The `Meeting` aggregate root is the sole manager of its inner state (including `lifecycle_state`, `version`, and `MeetingWorkflow` stages). API controllers, middleware, and background workers are forbidden from setting database columns directly. They must call explicit domain methods (e.g. `meeting.start_recording()`, `meeting.end_meeting()`).
2. **Centralized Invariants**:
   All lifecycle preconditions are checked inside the aggregate methods. Key invariants enforced:
   - **Start Precondition**: A meeting cannot start/record if it is already in `Ended` or `Archived` states.
   - **Chronology Constraint**: A meeting cannot end before its actual start timestamp (`actual_end >= actual_start`).
   - **Upload Invariant**: Audio files cannot be registered for upload unless the meeting room has transitioned to the `Recording` or `Ended` state.
   - **Archive Isolation**: A meeting cannot be archived while there are active `PENDING` or `PROCESSING` workflow stages.
   - **Active Deletion Restriction**: An active meeting (currently in the `Recording` state) cannot be deleted until it has been ended.
   - **Restart Restriction**: An `Archived` or `Ended` meeting cannot be returned to the `Recording` or `Waiting` state.
3. **Aggregate-Originated Events**:
   Domain events are generated internally by the aggregate during state transition calls, appended to an internal `events` list, and subsequently written to the outbox database table by the repository layer. This ensures events are only produced when business transitions successfully complete.
4. **Thin Controllers**:
   API endpoint handlers are restricted to:
   - Verifying the caller's IAM roles/permissions.
   - Retrieving the aggregate root from the repository.
   - Invoking the target domain method.
   - Saving the aggregate (database transaction manages versioning and outboxes).

---

## Consequences

- **Positive:** Business logic is isolated from Web APIs and database drivers, making it highly testable and refactor-resilient.
- **Positive:** Guarantees that the system cannot enter invalid states, regardless of API entry points.
- **Negative:** More domain-layer code is required to wrap simple mutations.
