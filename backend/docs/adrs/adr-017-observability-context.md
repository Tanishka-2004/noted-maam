# ADR-017: Platform Operations and Observability Bounded Context

**Status**: Accepted  
**Date**: 2026-07-10  
**Category**: Domain Architecture  
**Deciders**: Engineering Lead  

## Context

As the Noted Ma'am meeting operating system scales to 7 distinct bounded contexts, tracing asynchronous events, auditing API gateway latencies, diagnosing connection pings, and billing LLM tokens usage becomes critical. We need a standardized telemetry contract to isolate operations logic from business domains.

## Decision

We introduce a dedicated **Observability and Platform Operations Bounded Context**.

### Key Rules
- **The Telemetry Contract**: Every async block, event outbox payload, and HTTP gateway request must pass `trace_id`, `span_id`, and `parent_span_id`.
- **ContextVars Tracing**: request-scoped tracing context variables manage trace propagation safely across concurrent async loops, avoiding trace bleeding.
- **Categorized Metrics Taxonomy**: Metrics are explicitly structured into Platform, AI, Cost, Infrastructure, and Search schemas, avoiding ad-hoc naming.
- **Health Checks separation**: Liveness check endpoints (/live) run instantly, whereas Readiness check endpoints (/ready) query database, cache, and object storage connectivity states.

## Alternatives Considered

1. **Inline third-party API calls (e.g. direct Datadog/NewRelic inline)**: Restricts flexibility and introduces blocking external network delays.
2. **Context-less logs parsing**: Fails to correlate asynchronous outbox event worker chains back to original triggering HTTP gateway request threads.

## Consequences

- Diagnostic checks (/ready) allow automated container orchestration probes (Kubernetes, AWS ECS) to automatically route traffic away from degrading nodes.
- Correlated trace IDs simplify distributed debugging across worker processes.
