# ADR-002: Opaque Refresh Tokens with Rotation (RTR)

**Status:** Accepted  
**Date:** 2026-07-09  
**Deciders:** Platform Engineering Team  

---

## Context

We need long-lived credentials for maintaining user sessions without requiring
password re-entry. Candidates considered: long-lived JWTs, opaque tokens
(random bytes, stored server-side), sliding-session cookies.

---

## Decision

Use **opaque refresh tokens** — cryptographically random strings (`rt_` +
64 hex chars from two UUID4 values) stored server-side as SHA-256 hashes.
Implement **Refresh Token Rotation (RTR)**: every use of a refresh token issues
a new one and invalidates the previous. Replay detection: if an already-used
token is presented, the entire session family is revoked immediately.

---

## Rationale

| Criterion | Long-lived JWT | Opaque + RTR (chosen) |
|-----------|---------------|----------------------|
| Revocability | Not revocable without blocklist | Immediately revocable |
| Storage | Stateless (client-only) | Server-side hash store |
| Replay detection | Not possible | Family-wide revocation |
| Token theft detection | None | Detects within one rotation |
| Database dependency | None | PostgreSQL + index on hash |

Long-lived JWTs were rejected because they cannot be revoked. A stolen
long-lived JWT gives an attacker a 7-day persistent foothold with no
server-side defence.

---

## Token Family Design

```
Login → [Family F1]
  token_v1 (issued)
     ↓  rotate
  token_v2 (issued), token_v1 (is_used=True)
     ↓  rotate
  token_v3 (issued), token_v2 (is_used=True)

  token_v1 replay detected → all of F1 revoked
```

---

## Consequences

- **Positive:** Stolen tokens are detected on next legitimate use.
- **Positive:** Each token is single-use, limiting the replay window.
- **Negative:** Requires database lookup on every refresh. Mitigated by an
  index on `refresh_token_hash`.
- **Negative:** Parallel refresh requests from the same client (e.g., multiple
  tabs) may cause a false replay. Mitigated by the 15-minute access token TTL
  — most clients will not need to refresh simultaneously.

---

## Implementation

- `app/models/auth.py`: `Session` — `family_id`, `refresh_token_hash`,
  `is_used`, `is_revoked`, `expires_at`
- `app/services/identity.py`: `rotate_refresh_token()`, replay detection
- `app/api/auth.py`: `POST /refresh`, `POST /logout`
