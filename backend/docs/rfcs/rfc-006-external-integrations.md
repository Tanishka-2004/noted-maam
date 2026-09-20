# RFC-006: External Integrations Bounded Context

This RFC defines the architectural design, integration aggregate boundaries, adapter pattern interfaces, retry policies, and security credentials storage for the **External Integrations Bounded Context** within the **Noted Ma'am** Meeting Operating System.

---

## 1. Domain Boundaries & Responsibilities

The External Integrations Context connects internal meeting outcomes to external workspaces (Slack, webhooks) by acting as an asynchronous consumer of internal events.

```
       [Meeting Intelligence]
                 │
       (IntelligenceReportStatus.Completed)
                 │
                 ▼
     (MeetingIntelligenceReady Event)
                 │
                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ External Integrations Bounded Context                       │
  │                                                             │
  │  ├── [Integration Router]                                   │
  │  │     ├── [Mock Adapter]     ──> Simulates dispatches      │
  │  │     ├── [Slack Adapter]    ──> Channel Notifications     │
  │  │     └── [Webhook Adapter]  ──> HTTP Signature Deliveries │
  │  │                                                          │
  │  └── [Integration Outbox Worker & DLQ Log]                  │
  └─────────────────────────────────────────────────────────────┘
```

### Core Invariants

1. **Isolation of Failures**: Rate limits or network latencies from external integrations must never block internal transaction loops.
2. **At-Least-Once Delivery**: External tasks are tracked through an integration outbox queue supporting state transitions and incremental backoffs.
3. **Sandboxed Access control**: Configurations require explicit workspace ownership mapping. Credentials must be stored encrypted.
4. **Idempotency keys**: Outbound payloads are stamped with an idempotency key (`meeting_id:event_id:provider`) preventing duplicate posts on retry cycles.

---

## 2. Integration Aggregate Schema

We track configurations and tasks using two entity models:

### 2.1 IntegrationConfig
* `id`: UUID (Primary Key)
* `workspace_id`: UUID (Workspace mapping context)
* `provider`: String (`mock`, `slack`, `webhook`)
* `credentials_encrypted`: Encrypted credentials block
* `is_active`: Boolean
* `capabilities`: JSON map representing provider abilities (`supports_markdown`, `supports_threads`, etc.)

### 2.2 IntegrationOutbox
* `id`: UUID (Primary Key)
* `workspace_id`: UUID
* `integration_id`: UUID
* `idempotency_key`: String (Unique constraint)
* `status`: Enum (`Queued`, `Dispatching`, `Delivered`, `Retrying`, `DeadLetter`, `Cancelled`)
* `payload`: JSON data
* `attempt_count`: Integer
* `last_attempt_at`: DateTime
* `failure_reason`: String
* `http_status`: Integer
* `trace_id`: String (Tracing context correlation)

---

## 3. Adapter Pattern Contracts

We define a unified adapter interface:

```python
class IntegrationAdapter(ABC):
    @abstractmethod
    async def dispatch(self, payload: dict, config: dict) -> dict:
        """Executes API delivery tasks, returning success mappings or raising exceptions."""
        pass
```

### Supported Providers
* **MockIntegrationAdapter**: Standard mock simulator.
* **GenericWebhookAdapter**: Transmits JSON requests with HMAC signature headers verifying payload authenticity.
* **SlackAdapter**: Posts rich markdown summaries to channel targets.

---

## 4. Failure Classifications & Retries

To avoid infinite loops on unrecoverable bad requests, the worker classifies execution errors before scheduling retries:

### 4.1 Retryable Failures
Tasks are scheduled for backoff retries (up to 5 attempts) on:
* HTTP Status `429 Too Many Requests`
* HTTP Status `5xx Server Error`
* Connection Timeouts

### 4.2 Non-Retryable Failures
Tasks are moved directly to `DeadLetter` status on:
* HTTP Status `400 Bad Request`
* HTTP Status `401 Unauthorized` / `403 Forbidden`
* HTTP Status `404 Not Found`
* Malformed JSON payloads
