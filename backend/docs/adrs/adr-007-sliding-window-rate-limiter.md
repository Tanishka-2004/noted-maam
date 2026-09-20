# ADR-007: Redis Sliding Window Rate Limiter

**Status:** Accepted  
**Date:** 2026-07-09  
**Deciders:** Platform Engineering Team  

---

## Context

The authentication API must be protected against brute-force credential
stuffing, password spraying, and DoS attacks. A rate limiter must be the
outermost middleware layer — before authentication — so unauthenticated
flood traffic is dropped before it touches the database.

Candidates: token bucket, leaky bucket, fixed window, sliding window.

---

## Decision

Implement a **sliding window rate limiter** using Redis sorted sets.
Two tiers of limits enforced:
1. **IP-based**: 100 requests per 60 seconds per IP address
2. **User-based**: 20 requests per 60 seconds per authenticated user

The limiter is the **outermost middleware** — executes before `IAMMiddleware`.

---

## Rationale

| Algorithm | Burst tolerance | Memory | Boundary spike | Implementation |
|-----------|----------------|--------|----------------|----------------|
| Fixed window | Yes | Low | Vulnerable | Simple |
| Token bucket | Yes | Medium | Mitigated | Complex |
| Leaky bucket | No | Low | None | Simple |
| **Sliding window** | **Controlled** | **Medium** | **None** | **Moderate** |

Fixed window has a boundary spike problem: an attacker can send 200 requests
straddling a window boundary (100 at end of window N, 100 at start of N+1).
Sliding window eliminates this by counting requests in the last N seconds
relative to `now`, not relative to a fixed clock boundary.

---

## Redis Implementation

```python
# Pseudocode for sliding window check
now_ms = time.time() * 1000
window_start = now_ms - (window_seconds * 1000)

pipe = redis.pipeline()
pipe.zremrangebyscore(key, 0, window_start)   # prune old entries
pipe.zcard(key)                                # count current
pipe.zadd(key, {request_id: now_ms})          # record this request
pipe.expire(key, window_seconds)              # auto-expire key
results = pipe.execute()
count = results[1]
```

The pipeline is **atomic** — no race conditions between count and record.

---

## Failure Mode

If Redis is unavailable:
- Catch `RedisError`, log as WARNING
- **Fail open**: allow the request through
- This prevents a Redis outage from becoming a platform outage

---

## Middleware Execution Order

```
Request →  SlidingWindowRateLimiter (outermost)
         →  IAMMiddleware
         →  SecurityHeadersMiddleware (innermost)
         →  Route Handler
```

Rate limiting executes before authentication because:
1. Flood traffic from unauthenticated attackers must be dropped before any
   DB or Redis auth lookups occur.
2. IP-based rate limiting is meaningful even for anonymous endpoints.

---

## Consequences

- **Positive:** No boundary spike vulnerability.
- **Positive:** Unauthenticated flood traffic is stopped at the first layer.
- **Positive:** Redis pipeline ensures atomicity; no double-count race.
- **Negative:** Each request writes to Redis sorted set (~0.5ms overhead).
- **Negative:** IP-based limiting is naive against distributed attacks (many
  IPs). A future improvement would integrate with a WAF or Cloudflare's rate
  limiting.

---

## Implementation

- `app/core/rate_limiter.py`: `SlidingWindowRateLimiter`
- `app/main.py`: middleware registration order
