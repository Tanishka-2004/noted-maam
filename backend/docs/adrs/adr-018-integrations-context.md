# ADR-018: External Integrations Bounded Context

**Status**: Accepted  
**Date**: 2026-07-10  
**Category**: Domain Architecture  
**Deciders**: Engineering Lead  

## Context

Following the generation of structured meeting intelligence (Phase 6) and vector indexing (Phase 7), the platform needs to dispatch outcomes (summaries, action items, decisions) to external productivity platforms (Slack, webhooks) to integrate into user workflows.

Key challenges:
1. Deliveries to external SaaS APIs introduce transient failures, connection timeouts, and rate limits that must not block internal platform loops.
2. We must enforce workspace isolation and sandbox configuration controls.
3. Deliveries must be idempotent and support structured dead-letter logging for auditing.

## Decision

We isolate outbound deliveries into a dedicated **External Integrations Bounded Context**.

### Key Rules
- **Integration Aggregate**: Configured using `IntegrationConfig` (encrypted credentials, capabilities metadata) and executed using `IntegrationOutbox` (states: `Queued`, `Dispatching`, `Delivered`, `Retrying`, `DeadLetter`, `Cancelled`).
- **Idempotency Keying**: Outbound messages use the unique key format `meeting_id:report_id:provider` to prevent duplicate task tickets on retries.
- **Failures Classification**:
  - *Retryable Failures* (HTTP 429, 5xx, timeouts) increment attempts and retry up to 5 times.
  - *Non-Retryable Failures* (HTTP 400, 401, 403, 404, payload formatting) bypass retries and transition directly to the Dead-Letter Queue (DLQ).
- **HMAC Signatures**: Webhook payloads are signed with `HMAC-SHA256` payload-checksum headers verifying workspace authenticity.

## Alternatives Considered

1. **Inline API calls inside workers**: Creates failure coupling; a Slack timeout blocks the transcription finalization.
2. **Generic webhook tables**: Fails to provide configuration mapping or token rotations safeguards.

## Consequences

- The platform remains completely decoupled from external SaaS APIs. Adding Jira, GitHub, or MS Teams requires only adding provider adapters that conform to the `IntegrationAdapter` interface.
- Structured DLQ logging simplifies debugging and tracking.
