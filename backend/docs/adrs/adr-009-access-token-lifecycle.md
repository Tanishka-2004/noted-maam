# ADR-009: Access Token Lifecycle & Storage Policy

**Status:** Accepted  
**Date:** 2026-07-10  
**Deciders:** Platform Engineering & Security Architecture  

---

## Context

Access tokens are used to authorize requests. Storing access tokens in browser `localStorage` or `sessionStorage` makes them susceptible to extraction via Cross-Site Scripting (XSS) attacks. Additionally, returning access tokens in URL query parameters during federated login redirects (e.g. Google OAuth callbacks) exposes them in browser history, proxy/server logs, browser extensions, and the `Referer` header. 

We require a standardized access token lifecycle that minimizes these interception vectors across all current and future client applications.

---

## Decision

We establish a strict **Access Token Lifecycle and Storage Policy** with the following constraints:

1. **In-Memory Storage Only**: The frontend client must store short-lived `access_token` JWTs strictly in memory (React state / closure variables). It must never persist them to `localStorage`, `sessionStorage`, or custom browser databases (e.g. IndexedDB).
2. **Silent Refresh on Page Load**: When the page is reloaded, the client-side state is reset. The client must immediately perform a silent token rotation request (calling `POST /api/v1/auth/refresh`) using the browser-sent HttpOnly `refresh_token` cookie to restore active credentials.
3. **No Tokens in Redirect URLs**: The backend Google OAuth callback (`GET /api/v1/auth/oauth/google/callback`) must set the `refresh_token` as a secure, `HttpOnly`, `SameSite=Lax`, `/api/v1/auth/refresh`-bound cookie and issue a `307 Temporary Redirect` to the frontend landing path `/oauth/callback` without appending access tokens in the URL.
4. **Dynamic Expiry Scheduling**: The client must not refresh on a fixed interval. Instead, it must dynamically decode the active JWT `exp` claim and schedule token rotation to run **60 to 120 seconds before token expiration**.
5. **Idle Deferral & Backoff**: If the browser tab is hidden or the user is idle, token rotation is deferred until the app becomes visible again. Network errors during rotation must trigger exponential backoff.
6. **Mutex Refresh Queuing**: To resolve race conditions, multiple concurrent `401 Unauthorized` responses must queue up and share a single active `/refresh` promise rather than initiating multiple separate rotation requests.

---

## Access Token Lifecycle State Machine

```
   [ Unauthenticated ]
           │
      User Logins / OAuth
           │
           ▼
   [ Authenticating ] ── (Requests Access Token & Sets Cookie)
           │
       Success
           │
           ▼
    [ Authenticated ] <───┐
           │              │
    Token Near Expiry     │
           │              │
           ▼              │
     [ Refreshing ] ──────┘
           │
        Failure
           │
           ▼
      [ Expired ] ────► [ Logged Out ]
```

---

## Consequences

- **Positive:** Reduces the surface area for access token theft via XSS, as the token is not persistent in the browser storage.
- **Positive:** Prevents leakage of JWT access tokens in server/proxy logs or Referer headers.
- **Negative:** Page reloads trigger an additional round-trip API request to `/refresh` to restore user context, adding ~100ms of startup latency.
- **Complexity:** Requires client-side promise mutexes to handle concurrent API request failures during silent refresh cycles.

---

## Implementation

- **Backend**: `app/api/auth.py` redirects to `/oauth/callback` setting `refresh_token` cookie.
- **Frontend**: `src/features/auth/auth-service.ts` wraps fetch, manages memory token, queues failures, and retries.
- **Frontend**: `src/features/auth/auth-provider.tsx` dynamically schedules timeout based on exp parse and syncs cross-tab state.
- **Testing**: `tests/test_iam.py` validates redirect codes and cookies on callback.
