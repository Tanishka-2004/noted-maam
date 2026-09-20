# Case Study — Noted Ma'am: Distributed Meeting Operating System

## 1. Executive Summary
**Noted Ma'am** is an enterprise meeting operating system designed to ingest, process, summarize, index, and distribute meeting intelligence asynchronously. The platform transitions meetings from transient audio recordings into searchable, structured knowledge assets. 

It is designed as a modular backend composed of 9 isolated bounded contexts utilizing event-driven communication (Transactional Outbox), row-level multi-tenant database sandboxing (PostgreSQL RLS), and hybrid keyword-vector retrieval search.

---

## 2. Product Vision & Bounded Contexts
Meetings represent high-velocity corporate knowledge that is lost the moment a call ends. The platform acts as a secure, automated processor that extracts summaries, action items, decisions, and conflicts, publishing them to external workspaces (Slack, webhooks) while indexing them for sub-second semantic retrieval.

```
       [Next.js Web Frontend]
                 │
           (HTTP / HTTPS)
                 │
                 ▼
          [API Gateway]
                 │
  ┌──────────────┼──────────────┐
  │              │              │
[Identity]   [Meetings]    [Media Ingestion]
  │              │              │
  └──────┬───────┴──────┬───────┘
         ▼              ▼
     [Speech]     [Intelligence] ──> [Knowledge Index (RAG)]
         │              │
         └──────┬───────┘
                ▼
        [Observability] ──> [External Integrations]
```

---

## 3. Engineering Challenges & Core Architecture

### Challenge A: Strict Tenant Data Isolation (Row-Level Security)
* **Problem**: Storing multi-tenant business data in a shared database runs the risk of leakages. Relying on application-layer query filters (`WHERE workspace_id = X`) is highly error-prone.
* **Solution**: We integrated Python `ContextVars` to manage request-scoped workspace boundaries. The workspace ID is extracted from the RS256-signed JWT inside an HTTP middleware and injected into the SQLAlchemy connection lifecycle. Databases use row-level write and read restrictions.
* **Verification**: Verified via concurrent testing ensuring parallel async requests never bleed active context or leak row reads.

### Challenge B: Transactional Outbox Pattern for Consistent Eventing
* **Problem**: Dual-write operations (updating the database and sending events to a queue) can lead to inconsistency if the publisher fails after the database commit.
* **Solution**: We implemented the **Transactional Outbox Pattern**. Business state updates and outbox payloads are committed in a single database transaction. A separate dispatcher worker polls the outbox table, leases tasks, and publishes them with at-least-once guarantees.
* **Result**: Zero message loss during network partitions or worker restarts.

### Challenge C: High-Recall Hybrid Vector Retrieval
* **Problem**: Keyword search misses conceptual intent, while dense vector retrieval fails on specific identifiers (dates, IDs).
* **Solution**: We implemented a hybrid RAG search pipeline inside the **Knowledge Index** context. Input queries execute keyword matching (BM25) and semantic similarity matching (dense embeddings) concurrently. Rankings are combined using Reciprocal Rank Fusion (RRF) and reranked via a Cross-Encoder.
* **Result**: High accuracy combined with a strict Citation Verification layer that filters chunks referencing deleted transcript segments.

---

## 4. Operational Telemetry & Hardening

* **Distributed Tracing**: Trace context variables (`trace_id`, `span_id`) are propagated across API gateways, transactional outboxes, Redis streams, and background speech/intelligence workers.
* **Standardized Metrics**: Exposed via `/metrics` scrapable exporter capturing execution latencies, worker queue depths, and external dispatch retries broken down by provider.
* **SLOs**: Established target thresholds (ASR queues < 30s, search queries P95 < 200ms) with automated pager alerts.

---

## 5. Lessons Learned & Future Roadmap

### Lessons Learned
1. **Failure Classification**: Distinguishing between retryable errors (HTTP 429/500) and permanent client errors (HTTP 400/403) in integration workers saves CPU cycles and prevents queue blockages.
2. **Context Preservation**: Thread-safe ContextVars are critical in asynchronous Python backends to prevent telemetry tracing identifiers from bleeding across concurrent event loops.

### Future Roadmap
1. **Autonomous Replay Pipelines**: Implement administrative CLI tooling to replay Dead-Letter Queue (DLQ) integration payloads.
2. **Inbound Webhook Signature Gates**: Restrict inbound event webhook callbacks via HMAC signature verification.
