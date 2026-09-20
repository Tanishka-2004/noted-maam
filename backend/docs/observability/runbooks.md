# Operational Runbooks

This catalog contains step-by-step incident response procedures for mitigating Platform Operations SLO alerts.

---

## Runbook-001: Outbox Queue Depth Spike (`outbox_queue_depth`)

* **Alert Trigger**: `outbox_queue_depth > 100` for 5 minutes.
* **Possible Causes**:
  1. Outbox Event Dispatcher thread died or got blocked.
  2. High database write spikes matching UI events concurrency.
  3. Redis connectivity outage blocking event publishing.
* **Immediate Mitigation**:
  1. Inspect liveness status check: `GET /api/v1/health/live`.
  2. Check Redis connection liveness state: `GET /api/v1/health/ready`.
  3. Restart the backend ASGI application container or the standalone outbox dispatcher daemon process to release locks and restart polling.
* **Long-term Resolution**:
  * Expand outbox lease lock timeouts or configure concurrent batch dispatcher partition loops.

---

## Runbook-002: Transcription SLO Breach (`transcription_duration_ms`)

* **Alert Trigger**: P95 transcription duration exceeds 60 seconds.
* **Possible Causes**:
  1. Speech worker instances are fully saturated with long audio files.
  2. Whispering engine connection timeout or CPU throttling.
  3. MinIO storage network latency slowing raw audio downloads.
* **Immediate Mitigation**:
  1. Monitor active workers: check active thread counts on worker VMs.
  2. Spin up supplementary instances of `SpeechProcessingWorker` to auto-scale processing queues.
* **Long-term Resolution**:
  * Implement dynamic audio segment chunking before feeding audio streams to Whisper.

---

## Runbook-003: LLM Cost Budget Anomaly Alert (`estimated_cost`)

* **Alert Trigger**: Daily estimated USD cost exceeds $5.00/day.
* **Possible Causes**:
  1. Infinite retry loops in background intelligence workers.
  2. Prompt template size inflation.
* **Immediate Mitigation**:
  1. Query active worker process logs to isolate duplicate payload retries.
  2. Temporarily pause worker ingestion queues if necessary.
* **Long-term Resolution**:
  * Implement strict token rate limits at the gateway layer and caching for redundant prompt executions.
