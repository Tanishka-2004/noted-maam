# ADR-005: Redis as Permission Cache Layer

**Status:** Accepted  
**Date:** 2026-07-09  
**Deciders:** Platform Engineering Team  

---

## Context

Each authenticated request must resolve the user's workspace role and
permission set. Querying PostgreSQL on every request adds latency and load.

---

## Decision

Cache the resolved `{user_id}:{workspace_id}` permission set in **Redis** with
a 5-minute TTL. Cache key format: `perm:{user_id}:{workspace_id}`. On cache
miss, fetch from PostgreSQL and populate. On explicit role change, delete the
affected cache keys.

---

## Rationale

| Approach | Latency | Consistency | Complexity |
|----------|---------|-------------|-----------|
| PostgreSQL on every request | ~5–15ms | Perfect | Low |
| Redis cache (chosen) | ~0.3ms | 5-min eventual | Medium |
| In-process LRU cache | <0.1ms | Stale on restart | Low |

PostgreSQL-on-every-request would become a bottleneck at scale. In-process LRU
cache is incorrect in a multi-replica deployment (cache is not shared across
instances). Redis provides a shared cache consistent across all replicas.

---

## Cache Invalidation Strategy

```
Role assignment changed
  → DELETE perm:{user_id}:{workspace_id}
  → Next request re-fetches from DB
```

This is **explicit invalidation** — simpler and more predictable than
event-driven invalidation. For eventual consistency scenarios (e.g., role
downgrade not immediately reflected), the 5-minute TTL bounds the window.

---

## Failure Mode

If Redis is unavailable:
- `IAMMiddleware` catches `RedisError` and falls back to direct PostgreSQL lookup.
- This is intentional: **fail-open on the cache, not on auth**.
- A Redis outage increases DB load but does not block users.

---

## Consequences

- **Positive:** Per-request auth overhead reduced from ~10ms to ~0.3ms.
- **Positive:** Shared across replicas — consistent behaviour in scaled deployments.
- **Negative:** 5-minute window where a revoked role may still be cached.
  Acceptable for the current threat model; can be reduced to 1 minute if
  required.
- **Negative:** Additional infrastructure dependency (Redis). Mitigated by
  the DB fallback.

---

## Implementation

- `app/core/iam.py`: `_resolve_workspace_permissions()` with Redis cache
- Docker Compose: Redis 7 service with AOF persistence
