# RFC-005: Platform Operations & Observability Bounded Context

This RFC defines the architectural strategy, telemetry contracts, metrics taxonomy, health monitoring models, and operational runbooks for the **Observability and Platform Operations Bounded Context** within the **Noted Ma'am** Meeting Operating System.

---

## 1. Bounded Context & Telemetry Contract

Observability is isolated into its own bounded context. Business services emit signals but do not manage how logs, traces, or metrics are serialized, aggregated, or exported.

```
       [Identity]    [Meeting]    [Media]    [Speech]    [Intelligence]    [Index]
           │            │            │          │               │             │
           └────────────┼────────────┼──────────┼───────────────┼─────────────┘
                        ▼            ▼          ▼               ▼
          ┌─────────────────────────────────────────────────────────────┐
          │ Observability Context                                       │
          │                                                             │
          │  ├── [OpenTelemetry Tracer]    ──> Tracing Context Spans    │
          │  ├── [Prometheus Exporter]     ──> Latency & Counter Metrics│
          │  ├── [Cost & Token Monitor]    ──> AI Resource Usage Costs   │
          │  └── [Health check Registry]   ──> Heartbeats & Diagnostics  │
          └─────────────────────────────────────────────────────────────┘
                                │
                                ▼
               [Grafana / Prometheus Dashboard]
               [DLQ Monitoring & Alert Manager]
```

### The Telemetry Contract

Every HTTP request, outbox event, Redis stream consume, and background worker task must propagate trace identifiers inside their metadata block:
- `trace_id`: Unique identifier tracking the entire causal chain (e.g. `HTTP -> Speech -> Intelligence -> Index`).
- `span_id`: Identifier tracking the execution of the local unit of work.
- `parent_span_id`: Identifier linking the current unit of work back to its caller.

---

## 2. Standardized Metrics Taxonomy

Metrics are grouped into clean, uniform categories exported under `/metrics`:

### 2.1 Platform Performance
* `http_requests_total`: Counter tracking total requests (labels: `method`, `endpoint`, `status`).
* `http_request_duration_ms`: Histogram tracking response latency.
* `active_workers`: Gauge tracking processing workers.
* `active_users`: Gauge tracking concurrent authenticated sessions.

### 2.2 AI Model Telemetry
* `transcription_duration_ms`: Histogram tracking ASR/Whisper pipeline execution.
* `llm_generation_duration_ms`: Histogram tracking intelligence report summarization.
* `embedding_duration_ms`: Histogram tracking vector indexing runs.
* `reranking_duration_ms`: Histogram tracking Cross-Encoder query reranking.

### 2.3 Search Retrieval
* `search_latency`: Histogram tracking hybrid search times.
* `rrf_duration`: Histogram tracking reciprocal rank fusion runs.
* `reranker_latency`: Histogram tracking Cross-Encoder matching times.
* `retrieval_recall_at_10`: Gauge evaluating search quality.

### 2.4 Quality Telemetry
* `grounding_failures_total`: Counter tracking failed citations.
* `hallucination_rejected_total`: Counter tracking rejected chunks.
* `citation_validation_failures`: Counter tracking database citation integrity failures.
* `needs_review_total`: Counter tracking artifacts flagged for human review.

### 2.5 Cost Observability
* `tokens_prompt`: Counter tracking input token volume.
* `tokens_completion`: Counter tracking output token volume.
* `embedding_tokens`: Counter tracking vector token usage.
* `estimated_cost`: Counter tracking estimated USD API expenses.

### 2.6 Infrastructure
* `postgres_connections`: Gauge tracking database connection pool levels.
* `redis_latency`: Histogram tracking key-value store retrieval times.
* `s3_upload_duration`: Histogram tracking object storage chunk write times.
* `outbox_queue_depth`: Gauge tracking pending outbox event table count.

---

## 3. Health & Readiness Models

We separate system check queries into liveness and readiness interfaces:

* **/live**: Returns `200 OK` instantly, indicating the python application thread is executing.
* **/ready**: Verifies active connectivity to required upstream systems before reporting healthy:
  * PostgreSQL connection ping.
  * Redis connection ping.
  * MinIO Object Storage connection ping.
  * Heartbeat checks from background worker daemons.

---

## 4. Operational Service Level Objectives (SLOs)

We target operational SLO thresholds monitored by alerts:

| Service | SLO Target |
| --- | --- |
| Authentication | 99.9% availability |
| Transcript generation | P95 < 60 seconds |
| Meeting Intelligence | P95 < 30 seconds |
| Search | P95 < 200 ms |
| Indexing | P95 < 15 seconds |
