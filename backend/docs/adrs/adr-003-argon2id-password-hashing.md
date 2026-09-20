# ADR-003: Argon2id for Password Hashing

**Status:** Accepted  
**Date:** 2026-07-09  
**Deciders:** Platform Engineering Team  

---

## Context

We need a password hashing algorithm that is resistant to GPU-accelerated
brute force. Candidates: bcrypt, scrypt, PBKDF2, Argon2id.

---

## Decision

Use **Argon2id** (winner of Password Hashing Competition, 2015) via the
`argon2-cffi` library. Enforce OWASP-recommended parameters:
memory cost ≥ 19 MiB, iterations ≥ 2, parallelism ≥ 1.

Augment with:
- **zxcvbn** entropy scoring (minimum score 3/4)
- **HIBP k-anonymity** breach check (rejects passwords found ≥ 1 times)

---

## Rationale

| Algorithm | GPU resistance | Memory-hard | PHC winner | OWASP recommended |
|-----------|---------------|-------------|-----------|-------------------|
| bcrypt | Moderate | No | No | Acceptable |
| scrypt | High | Yes | No | Recommended |
| PBKDF2 | Low | No | No | Legacy only |
| Argon2id | Highest | Yes | ✅ Yes | ✅ Yes |

Argon2id (hybrid of Argon2i + Argon2d) provides:
- Side-channel resistance (Argon2i component)
- GPU/ASIC resistance (memory-hard Argon2d component)

---

## HIBP k-Anonymity Protocol

```
1. Hash password with SHA-1
2. Send first 5 hex chars to api.pwnedpasswords.com/range/{prefix}
3. API returns all suffixes with breach counts
4. Check if our suffix appears in the list
5. On HIBP timeout/error → fail open (do not block registration)
```

Fail-open prevents HIBP outages from blocking legitimate registrations.

---

## Consequences

- **Positive:** Industry-highest resistance to offline cracking attacks.
- **Positive:** zxcvbn + HIBP eliminates the majority of weak/common passwords
  before they reach the database.
- **Negative:** Argon2id is ~50–100ms per hash. Acceptable for login/register;
  never called in hot paths.
- **Risk:** HIBP API dependency. Mitigated by the fail-open fallback.

---

## Implementation

- `app/core/security.py`: `hash_password()`, `verify_password()`, `is_password_pwned()`
- `app/services/identity.py`: `register_user()` — zxcvbn + HIBP pre-check
