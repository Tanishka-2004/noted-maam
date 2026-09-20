# Noted Ma'am: Production Readiness Review & Portfolio Pack

This document outlines the **Production Readiness Review (PRR)** and the **STAR Interview Architecture Stories** for the **Noted Ma'am** Meeting Operating System.

---

## 1. Production Readiness Review (PRR)

### 1.1 Service Level Objectives (SLOs) & Alert Catalog

| Service / Path | SLI Metrics | Target SLO | Warning Alert | Critical Escalation |
| --- | --- | --- | --- | --- |
| **Authentication** | Request Latency | P95 < 100ms | P95 > 150ms for 2m | P95 > 300ms for 5m |
| **Search** | Hybrid Query Latency | P95 < 200ms | P95 > 300ms for 2m | P95 > 500ms for 5m |
| **Speech Worker** | Queue Wait Time | P95 < 30s | Queue > 60s | Queue > 5m or OOM |
| **Intelligence** | Processing time | P95 < 60s | Processing > 90s | Processing > 3m |
| **Outbound Webhooks** | Outbox Queue Depth | Queue size < 10 | Queue > 50 for 5m | Queue > 200 or DLQ spike |

---

### 1.2 Disaster Recovery (DR) Plan
* **Recovery Point Objective (RPO)**: 1 hour (PostgreSQL WAL archiving, incremental S3 hourly snapshots).
* **Recovery Time Objective (RTO)**: 15 minutes (Automated Helm rollback deployment, active-passive database failover promotion).

---

### 1.3 Chaos Engineering Runbooks

#### Experiment 001: Cache Outage (Redis Failover)
* **Hypothesis**: Killing the primary Redis node drops the permissions cache. The system should automatically fall back to Postgres queries.
* **Verification**: Verify that HTTP requests to authenticated endpoints bypass cache, query database, and complete successfully with P95 latency remaining under 250ms.

#### Experiment 002: Worker Partition (ASR Crash)
* **Hypothesis**: Killing the `SpeechProcessingWorker` process mid-execution should halt transcriptions but keep HTTP API gateways fully responsive.
* **Verification**: Verify that meeting recordings can still be uploaded and the `outbox_queue_depth` metric grows, but no HTTP gateway drops traffic. Upon restarting the worker, processing resumes automatically.

---

## 2. STAR Interview Architecture Stories

### 2.1 Story: Row-Level Workspace Isolation (Phase 1 & 2)
* **Situation**: Building a multi-tenant platform where a data leak between workspaces is a critical risk. Relying on application-layer `WHERE` clauses is error-prone.
* **Task**: Implement request-scoped, row-level tenant sandboxing that enforces strict data isolation at the database layer.
* **Action**: We integrated Python `ContextVars` inside ASGI middleware (`IAMMiddleware`) to capture the tenant's workspace ID from the JWT at the request gate. This context was propagated down to the SQLAlchemy session lifecycle, executing a PostgreSQL-equivalent schema isolation filter.
* **Result**: We achieved zero-leak database operations, verified by concurrency tests ensuring that concurrent tenant requests never bleed context.

### 2.2 Story: Transactional Outbox Pattern (Phase 3)
* **Situation**: Network failures during event publishing can lead to data inconsistency. If a database transaction commits successfully but the Redis stream fails, the speech worker never starts.
* **Task**: Guarantee at-least-once event delivery.
* **Action**: We implemented the **Transactional Outbox Pattern**. Business logic changes and event payload records are saved in the same database transaction. A separate background dispatcher polls the outbox table and publishes events, tracking leases.
* **Result**: Delivered 100% event consistency under network failures, tested by simulating dispatcher crashes mid-transaction.

### 2.3 Story: Hybrid Retrieval Search Pipeline (Phase 7)
* **Situation**: Semantic vector search can suffer from low precision for exact-word queries, while BM25 lacks conceptual understanding.
* **Task**: Design a high-precision search pipeline.
* **Action**: We built a hybrid pipeline in the **Knowledge Index** context. Queries execute concurrently across BM25 keyword matching and Cosine vector similarity. Rankings are merged using Reciprocal Rank Fusion (RRF) and refined with a Cross-Encoder Reranker.
* **Result**: High search quality with a strict permission-gated Citation Validator that automatically filters out results referencing deleted utterances.
