# ADR-010: Meeting Aggregate Boundaries & Encapsulation

**Status:** Accepted  
**Date:** 2026-07-10  
**Deciders:** Platform Engineering & Security Architecture  

---

## Context

In complex domains, database schemas are often modified arbitrarily by API controllers or services, bypassing business rules and invariants. For example, setting `meeting.lifecycle_state = "Recording"` from an API handler can result in corrupt states if other preconditions are ignored. 

To maintain state consistency and enforce business invariants, we need strict aggregate boundaries around the `Meeting` entity.

---

## Decision

1. **Encapsulated Self-Mutation**: Only the `Meeting` aggregate class may mutate its own state. API controllers and services cannot modify state fields directly. Instead, they must invoke explicit domain methods on the aggregate (e.g., `meeting.start_recording(user_id, timestamp)`, `meeting.end_meeting(timestamp)`).
2. **Centralized Invariant Enforcement**: Every state transition method must assert its own preconditions (e.g. check current states, verify user permissions context, confirm recording constraints) and raise clear domain exceptions if violated.
3. **Optimistic Concurrency Control**: We will add a `version` column (integer) to the `meetings` table. Any write operation must verify the version using optimistic locking to prevent race conditions (e.g., two hosts trying to end or record a meeting simultaneously). If a conflict occurs, the database transaction fails and raises an optimistic locking error, prompting the client to retry.
4. **Clock Abstraction**: We will inject a `Clock` service/interface (utilizing a default system clock `Clock.now()` returning timezone-aware timestamps) instead of invoking raw `datetime.utcnow()` inside the aggregate. This ensures state mutation times are deterministic and easily stubbed in tests.

---

## Consequences

- **Positive:** Business rules are centralized in the domain model rather than scattered in API endpoints or background services.
- **Positive:** Optimistic locking prevents lost updates and concurrent command race condition corruptions.
- **Positive:** A Mock/Static Clock simplifies testing time-dependent lifecycle transitions (e.g. meeting expiry, scheduled start leeway checks).
- **Negative:** Increased boilerplate in the entity code.
- **Negative:** Clients must handle version conflict retries on concurrent requests.

---

## Implementation

- **Model**: `app/models/meeting.py` holds aggregate rules and transition methods.
- **Concurrency**: SQLAlchemy `version_id_col` configuration implements the optimistic concurrency locking.
- **Clock**: `app/core/clock.py` defines the clock interface and native system clock helper.
