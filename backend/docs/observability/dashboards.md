# Grafana Operational Dashboards

This document maps out the layout, queries, and visualizations for our Prometheus-backed Grafana dashboards monitoring the **Platform Operations & Observability Bounded Context**.

---

## 1. System Health & Performance Dashboard

### 1.1 HTTP Throughput & Latency
* **Visualization**: Graph (Left: Request Rates, Right: Durations)
* **Queries**:
  * Request volume: `sum(rate(http_requests_total[5m])) by (status, method)`
  * P95 API Latency: `histogram_quantile(0.95, sum(rate(http_request_duration_ms_bucket[5m])) by (le))`
* **SLO Alert Threshold**: P95 Latency > 200ms (HTTP Gateway).

### 1.2 DB Connection Pool & Saturation
* **Visualization**: Gauge & Stacked Area
* **Queries**:
  * PostgreSQL Connections: `postgres_connections`
  * Outbox Queue Depth: `outbox_queue_depth`
* **SLO Alert Threshold**: Queue depth > 100 continuously for 5 minutes.

---

## 2. AI Processing Pipeline Dashboard

### 2.1 Audio Transcription (Whisper & Pyannote)
* **Visualization**: Singlestat Gauge & Histograms
* **Queries**:
  * P95 Transcription Duration: `histogram_quantile(0.95, sum(rate(transcription_duration_ms_bucket[5m])) by (le))`
* **SLO Target**: P95 < 60 seconds.

### 2.2 Intelligence Reports Generation (Gemini)
* **Visualization**: Singlestat Gauge & Trend Graph
* **Queries**:
  * P95 LLM Generation Duration: `histogram_quantile(0.95, sum(rate(llm_generation_duration_ms_bucket[5m])) by (le))`
* **SLO Target**: P95 < 30 seconds.

---

## 3. Cost & Token Usage Dashboard

### 3.1 Prompt vs Completion Tokens
* **Visualization**: Bar Gauge / Stacked Bar
* **Queries**:
  * Prompt input: `rate(tokens_prompt[24h])`
  * Completion output: `rate(tokens_completion[24h])`
  * Embedding inputs: `rate(embedding_tokens[24h])`

### 3.2 Total Financial Run Cost (USD)
* **Visualization**: Large Singlestat Value (USD)
* **Query**:
  * Cumulative monthly budget: `sum(estimated_cost)`
* **Alert Trigger**: Cost projection exceeding $50.00/month anomaly.

---

## 4. Search & Retrieval Quality Dashboard

### 4.1 Hybrid Search Execution Latency
* **Visualization**: Graph
* **Queries**:
  * P95 Search: `histogram_quantile(0.95, sum(rate(search_latency_bucket[5m])) by (le))`
  * P95 RRF Combine: `histogram_quantile(0.95, sum(rate(rrf_duration_bucket[5m])) by (le))`
* **SLO Target**: P95 < 200 ms.

### 4.2 Retrieval Quality & Citations Accuracy
* **Visualization**: Gauge
* **Queries**:
  * Grounding failures count: `grounding_failures_total`
  * Citation integrity validation errors: `citation_validation_failures`
  * Hallucination rejections: `hallucination_rejected_total`
