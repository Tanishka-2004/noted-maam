# Authentication Sequence Diagrams

Sequence diagrams for all authentication and session management flows in the
Noted Ma'am Identity Service. These diagrams are normative — implementation
must match.

---

## 1. Registration Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant RateLimiter
    participant API as Auth API
    participant IdentityService
    participant Security as security.py
    participant HIBP as HIBP API
    participant DB as PostgreSQL

    User->>Frontend: Fill registration form
    Frontend->>RateLimiter: POST /api/v1/auth/register
    RateLimiter->>API: Pass (under threshold)
    API->>IdentityService: register_user(email, password)
    IdentityService->>DB: Query: email exists?
    DB-->>IdentityService: User or None

    alt Email already active
        IdentityService-->>API: raise ValueError("already registered")
        API-->>Frontend: 400 Bad Request
    else Pending verification (re-register)
        IdentityService->>IdentityService: Reset verification token
    else New user
        IdentityService->>Security: zxcvbn score check
        Security-->>IdentityService: score >= 3 ✅
        IdentityService->>HIBP: k-anonymity SHA1 prefix check
        HIBP-->>IdentityService: Not breached ✅
        IdentityService->>Security: hash_password(password) [Argon2id]
        Security-->>IdentityService: password_hash
        IdentityService->>DB: INSERT User (is_active=False)
        IdentityService->>DB: INSERT Invitation (verification_token_hash, expires_at+24h)
        IdentityService-->>API: UserResponse
        API-->>Frontend: 201 Created
        Note over IdentityService,DB: Email verification link sent (background)
    end
```

---

## 2. Email Verification Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API as Auth API
    participant IdentityService
    participant DB as PostgreSQL

    User->>Frontend: Click email verification link
    Frontend->>API: POST /api/v1/auth/verify?token=<raw_token>
    API->>IdentityService: verify_email(token)
    IdentityService->>IdentityService: SHA256(token) → token_hash
    IdentityService->>DB: Query Invitation by token_hash
    DB-->>IdentityService: Invitation record

    alt Token not found
        IdentityService-->>API: raise ValueError("invalid token")
        API-->>Frontend: 400 Bad Request
    else Token expired
        IdentityService-->>API: raise ValueError("token expired")
        API-->>Frontend: 400 Bad Request
    else Token valid
        IdentityService->>DB: UPDATE User: is_active=True, is_email_verified=True
        IdentityService->>DB: UPDATE Invitation: is_accepted=True
        IdentityService->>DB: INSERT Workspace + WorkspaceMembership (role=Owner)
        IdentityService-->>API: UserResponse
        API-->>Frontend: 200 OK
    end
```

---

## 3. Login Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant RateLimiter
    participant API as Auth API
    participant IdentityService
    participant Security as security.py
    participant JWKS as JWKSManager
    participant DB as PostgreSQL

    User->>Frontend: Enter credentials
    Frontend->>RateLimiter: POST /api/v1/auth/login
    RateLimiter->>API: Pass (under IP threshold)
    API->>IdentityService: login_user(email, password, ip, ua)
    IdentityService->>DB: Query User by email
    DB-->>IdentityService: User or None

    alt User not found or no password_hash
        IdentityService-->>API: raise ValueError("Invalid email or password")
        API-->>Frontend: 401 Unauthorized
    else User not active (unverified)
        IdentityService-->>API: raise ValueError("Account pending verification")
        API-->>Frontend: 401 Unauthorized
    else
        IdentityService->>Security: verify_password(password, hash) [Argon2id]
        Security-->>IdentityService: match ✅

        alt Session limit (>=10 active)
            IdentityService->>DB: REVOKE oldest session
        end

        IdentityService->>JWKS: get_active_key()
        JWKS-->>IdentityService: JWKSKey (RS256 private key)
        IdentityService->>JWKS: sign_token(payload) → access_token (15min)
        IdentityService->>DB: INSERT Session (opaque rt, family_id, is_used=False)
        IdentityService->>DB: INSERT Device (browser, OS, IP, UA)
        IdentityService-->>API: (user, access_token, refresh_token)
        API->>Frontend: Set-Cookie: refresh_token=<opaque> HttpOnly Secure
        API-->>Frontend: 200 OK { access_token }
    end
```

---

## 4. Token Refresh + RTR Replay Detection

```mermaid
sequenceDiagram
    actor Client
    participant API as Auth API
    participant IdentityService
    participant JWKS as JWKSManager
    participant DB as PostgreSQL

    Client->>API: POST /api/v1/auth/refresh [cookie: refresh_token]
    API->>IdentityService: rotate_refresh_token(old_rt)
    IdentityService->>IdentityService: SHA256(old_rt) → old_hash
    IdentityService->>DB: Query Session by refresh_token_hash

    alt Session not found
        IdentityService-->>API: raise ValueError("Invalid refresh token")
        API-->>Client: 401 Unauthorized
    else Session revoked or expired
        IdentityService-->>API: raise ValueError("Revoked or expired")
        API-->>Client: 401 Unauthorized
    else is_used = True (REPLAY DETECTED)
        IdentityService->>DB: UPDATE all sessions WHERE family_id=X: is_revoked=True
        IdentityService->>DB: AuditLog: "token_replay_detected" CRITICAL
        IdentityService-->>API: raise ValueError("Token family compromise detected")
        API-->>Client: 401 Unauthorized
    else Normal rotation
        IdentityService->>DB: UPDATE Session: is_used=True
        IdentityService->>JWKS: sign_token(new_payload) → new_access_token (15min)
        IdentityService->>DB: INSERT new Session (new_rt, same family_id)
        IdentityService-->>API: (new_access_token, new_refresh_token)
        API->>Client: Set-Cookie: refresh_token=<new_rt>
        API-->>Client: 200 OK { access_token }
    end
```

---

## 5. IAM Middleware Request Pipeline

```mermaid
sequenceDiagram
    participant Client
    participant RateLimiter as SlidingWindowRateLimiter
    participant IAM as IAMMiddleware
    participant Redis
    participant JWKS as JWKSManager
    participant DB as PostgreSQL
    participant Handler as Route Handler

    Client->>RateLimiter: Any request
    RateLimiter->>Redis: Sliding window check (IP + user)

    alt Rate limit exceeded
        RateLimiter-->>Client: 429 Too Many Requests
    else Under limit
        RateLimiter->>IAM: Forward request

        alt Public route (e.g., /health, /api/v1/auth/login)
            IAM->>Handler: Forward (no auth check)
        else Protected route
            IAM->>IAM: Extract Bearer token
            IAM->>JWKS: verify_token(token) [RS256, aud, kid]

            alt Invalid / expired / forged token
                IAM-->>Client: 401 Unauthorized
            else Valid token
                IAM->>Redis: GET perm:{user_id}:{workspace_id}

                alt Cache hit
                    Redis-->>IAM: permission_set
                else Cache miss
                    IAM->>DB: Query WorkspaceMembership
                    DB-->>IAM: role + permissions
                    IAM->>Redis: SET perm:{user_id}:{workspace_id} TTL=300s
                end

                IAM->>IAM: workspace_ctx.set(workspace_id)
                IAM->>IAM: user_ctx.set(user_id)
                IAM->>DB: SET LOCAL app.workspace_id = '{workspace_id}' [RLS]
                IAM->>Handler: Forward request
                Handler-->>IAM: Response
                IAM->>IAM: workspace_ctx.reset() / user_ctx.reset()
                IAM-->>Client: Response + Security Headers
            end
        end
    end
```

---

## 6. Google OAuth Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API as Auth API
    participant Google as Google OAuth
    participant IdentityService
    participant DB as PostgreSQL

    User->>Frontend: Click "Sign in with Google"
    Frontend->>API: GET /api/v1/auth/oauth/google/authorize
    API->>API: state = secrets.token_urlsafe(32)
    API->>Frontend: Set-Cookie: oauth_state=<state> HttpOnly
    API-->>Frontend: 302 Redirect → Google OAuth URL

    User->>Google: Authorize app
    Google->>API: GET /api/v1/auth/oauth/google/callback?code=X&state=Y

    API->>API: Compare ?state vs cookie oauth_state
    alt State mismatch (CSRF)
        API-->>Frontend: 401 Unauthorized
    else State matches
        API->>Google: Exchange code → access_token + id_token
        Google-->>API: UserProfile (email, name, google_id)
        API->>IdentityService: handle_oauth_callback(profile)
        IdentityService->>DB: Query User by email

        alt New user
            IdentityService->>DB: INSERT User (is_active=True, verified via Google)
            IdentityService->>DB: INSERT OAuthIdentity (provider=google)
        else Existing user — link identity
            IdentityService->>DB: INSERT OAuthIdentity (link to existing user)
        end

        IdentityService->>DB: INSERT Session + Device
        IdentityService-->>API: (user, access_token, refresh_token)
        API->>Frontend: Set-Cookie: refresh_token HttpOnly Secure
        API-->>Frontend: 200 OK { access_token }
    end
```

---

## 7. WebSocket Authentication Handshake

```mermaid
sequenceDiagram
    actor Client
    participant WS as WebSocket Endpoint
    participant IAMHelper as get_websocket_user()
    participant JWKS as JWKSManager

    Client->>WS: WS Connect /ws/meeting/{id}?token=<jwt>
    WS->>IAMHelper: get_websocket_user(websocket)
    IAMHelper->>IAMHelper: token = websocket.query_params.get("token")

    alt No token
        IAMHelper-->>WS: raise WebSocketException(1008, "Missing token")
        WS-->>Client: Close 1008
    else Token present
        IAMHelper->>JWKS: verify_token(token)

        alt Invalid / expired / forged
            IAMHelper-->>WS: raise WebSocketException(1008, "Invalid token")
            WS-->>Client: Close 1008
        else Valid
            IAMHelper-->>WS: user_id (UUID)
            WS->>Client: Connection accepted
            Note over Client,WS: Bidirectional streaming begins
        end
    end
```
