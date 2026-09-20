# ADR-001: JWT Algorithm — RS256 with JWKS Rotation

**Status:** Accepted  
**Date:** 2026-07-09  
**Deciders:** Platform Engineering Team  

---

## Context

We need a token format for authenticating API requests across microservices.
Candidates considered: HS256 (symmetric HMAC), RS256 (asymmetric RSA), EdDSA.

---

## Decision

Use **RS256** (RSA with SHA-256) for signing JWTs. Publish public keys as a
JWKS endpoint (`/.well-known/jwks.json`). Rotate keys every 30 days with a
24-hour grace period so existing tokens remain valid through rotation.

---

## Rationale

| Criterion | HS256 | RS256 (chosen) | EdDSA |
|-----------|-------|---------------|-------|
| Shared secret leakage risk | High | None | None |
| Downstream service verification | Requires secret distribution | Public key only | Public key only |
| Key rotation support | Complex | Simple JWKS | Simple JWKS |
| Algorithm confusion attacks | Vulnerable (with weak impl.) | Mitigated (explicit `algorithms=["RS256"]`) | N/A |
| Industry adoption | Widespread | Widespread | Growing |

**RS256 was chosen over EdDSA** because PyJWT's RS256 support is more mature,
and all major identity providers (Okta, Auth0, Cognito) publish RS256 JWKS
endpoints, making our format interoperable.

---

## Consequences

- **Positive:** Downstream services verify tokens using public keys only.
  Auth service never needs to share secrets with consumers.
- **Positive:** Key rotation is transparent — old tokens remain valid during
  the grace window via the `kid` header lookup.
- **Negative:** RSA key generation is slower than HMAC. Acceptable at login
  frequency; token verification uses cached public keys.
- **Risk mitigated:** Algorithm confusion attack (HS256 with public key as
  HMAC secret) is blocked by specifying `algorithms=["RS256"]` explicitly in
  `jwt.decode()`.

---

## Implementation

- `app/core/jwks.py`: `JWKSManager` — key pool, rotation, `verify_token()`
- `app/api/auth.py`: `GET /.well-known/jwks.json`
- `app/core/iam.py`: `IAMMiddleware.verify_token()`
