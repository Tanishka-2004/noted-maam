# ADR-008: OAuth as an External Identity Provider Framework

**Status:** Accepted  
**Date:** 2026-07-09  
**Deciders:** Platform Engineering Team  

---

## Context

Users should be able to sign in with existing Google accounts. Future phases
may require Microsoft, GitHub, Okta, or SAML providers. The OAuth integration
must be designed as a framework, not a single-provider implementation.

---

## Decision

Design OAuth as an **External Identity Provider (IdP) Framework**. All providers
implement a common `ExternalIdentityProvider` interface. Google OAuth 2.0 with
PKCE is Provider #1. Each provider handles its own authorization URL generation,
code exchange, and profile normalization into a `ExternalProfile` dataclass.

CSRF protection: **state parameter** generated as a cryptographically secure
random string, stored in an HttpOnly `oauth_state` cookie, and validated on
callback.

Account linking: if a user's email already exists with a password account,
the OAuth identity is linked to the existing account (no duplicate users).

---

## Provider Interface

```python
class ExternalIdentityProvider(ABC):
    @abstractmethod
    def get_authorization_url(self, state: str) -> str: ...

    @abstractmethod
    def exchange_code_for_profile(
        self, code: str, state: str, expected_state: str
    ) -> ExternalProfile: ...
```

Adding a new provider requires implementing two methods. No changes to
`IdentityService` or the auth routes.

---

## CSRF Mitigation

```
1. Generate state = secrets.token_urlsafe(32)
2. Store in HttpOnly cookie: oauth_state=<state>
3. Redirect user to provider with ?state=<state>
4. On callback: compare query ?state with cookie value
5. If mismatch → 401 (CSRF detected)
6. Clear the cookie after validation
```

The cookie is HttpOnly to prevent JavaScript from reading it (XSS resilience).

---

## Account Linking Matrix

| Scenario | Result |
|----------|--------|
| New email via OAuth | Create account, link identity |
| Existing unverified password account | Link OAuth, activate account |
| Existing verified password account | Link OAuth identity to account |
| OAuth with same provider + email already linked | Return existing session |

---

## Consequences

- **Positive:** Adding provider #2 (Microsoft, GitHub) requires no changes to
  core auth logic — only a new class implementing the interface.
- **Positive:** CSRF state validation prevents open redirect and code injection.
- **Negative:** Account linking creates complexity around which identity is
  "primary". Resolved by treating email as the canonical identity anchor.
- **Risk:** Provider token exchange happens server-side only — never
  client-side. This prevents code interception attacks.

---

## Implementation

- `app/core/identity_providers.py`: `ExternalIdentityProvider`, `GoogleOAuthProvider`
- `app/services/identity.py`: `handle_oauth_callback()`, `link_oauth_identity()`
- `app/api/auth.py`: `GET /oauth/{provider}/authorize`, `GET /oauth/{provider}/callback`
