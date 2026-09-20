# ADR-006: Python contextvars for Request-Scoped Workspace Isolation

**Status:** Accepted  
**Date:** 2026-07-09  
**Deciders:** Platform Engineering Team  

---

## Context

`IAMMiddleware` must propagate the resolved `workspace_id` and `user_id` to
downstream service and repository layers within a single async request context,
without passing them as explicit function arguments through every layer.

Candidates: thread-local storage, FastAPI `Request.state`, Python `contextvars`.

---

## Decision

Use Python's built-in `contextvars.ContextVar` for request-scoped state.
Set `workspace_ctx` and `user_ctx` at the start of each request in
`IAMMiddleware`. Clear them at the end of the request.

---

## Rationale

| Approach | Async-safe | Implicit propagation | Multi-thread safe |
|----------|-----------|---------------------|------------------|
| `threading.local` | ❌ No | Yes | Yes (per-thread) |
| `Request.state` | ✅ Yes | No (must pass Request) | Yes |
| **`contextvars`** | ✅ **Yes** | ✅ **Yes** | ✅ **Yes** |

`threading.local` is incorrect in async code: `asyncio` runs coroutines on a
single thread, so thread-local state is shared across concurrent requests.

`Request.state` requires passing `request` through every function call —
breaking separation of concerns between API and service layers.

`contextvars` are designed for exactly this use case: each `asyncio.Task` gets
an isolated copy of the context, preventing cross-request contamination.

---

## Safety Guarantee

```python
# IAMMiddleware sets context at request start
workspace_ctx.set(resolved_workspace_id)

# Service layer reads without needing the request object
ws_id = workspace_ctx.get()

# Token is stored and reset at request end to prevent leakage
token = workspace_ctx.set(value)
...
workspace_ctx.reset(token)
```

The `reset()` call after response guarantees no state bleeds between requests
even if an exception is raised (implemented in `finally` block).

---

## Consequences

- **Positive:** Service and repository layers are decoupled from FastAPI's
  `Request` object.
- **Positive:** Correct in async environments; no shared state across requests.
- **Negative:** Implicit propagation can make request context harder to trace
  in debugging. Mitigated by structured logging that always includes
  `workspace_id` and `user_id`.

---

## Implementation

- `app/core/iam.py`: `workspace_ctx`, `user_ctx` ContextVar declarations
- `IAMMiddleware.dispatch()`: `set()` before yield, `reset()` in finally
