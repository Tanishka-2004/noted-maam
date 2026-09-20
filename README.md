# NOTED MA'AM — Enterprise Meeting Operating System

> *"Meetings End. Work Begins."*

Noted Ma'am is an AI-native meeting intelligence platform designed to ingest
multilingual meeting streams (English, Hindi, Hinglish), execute real-time
diarization, and automatically resolve deliverables — tasks, action items,
decisions, and structural conflicts.

---

## Phase 2 — Identity & Access Management (Implemented)

The IAM subsystem is the security boundary of the platform. Every future
service depends on it. It has been designed and tested to production standards
before Meeting Lifecycle or AI pipeline work begins.

### What is implemented

| Component | Status | Coverage |
|-----------|--------|----------|
| RS256 JWT + JWKS key rotation | ✅ | 98% |
| Opaque refresh tokens + RTR | ✅ | 83% |
| Replay detection + family revocation | ✅ | 83% |
| Argon2id password hashing | ✅ | 74% |
| zxcvbn entropy + HIBP k-anonymity | ✅ | 74% |
| Registration idempotency | ✅ | 88% |
| Email verification flow | ✅ | 88% |
| PostgreSQL Row-Level Security | ✅ | 80% |
| Redis permission cache | ✅ | 80% |
| `contextvars` workspace isolation | ✅ | 80% |
| Session & device management | ✅ | 88% |
| Concurrent session limit (max 10) | ✅ | 83% |
| Google OAuth + account linking | ✅ | 50% |
| Redis sliding window rate limiter | ✅ | 80% |
| Security headers middleware | ✅ | 77% |
| WebSocket JWT authentication | ✅ | 80% |
| Audit logging (all security events) | ✅ | 83% |
| **Total test coverage (84%)** | ✅ | **84%** |
| **Security test suite (52 tests)** | ✅ | **52 pass** |

### Security architecture

```
Request → SlidingWindowRateLimiter (IP: 100/60s, User: 20/60s)
        → IAMMiddleware (RS256 JWT verify → Redis permission cache → RLS context)
        → SecurityHeadersMiddleware (CSP, HSTS, X-Frame-Options, nosniff)
        → Route Handler
        → Response
```

### Architecture Decision Records

All significant design decisions are documented:

| ADR | Decision |
|-----|----------|
| [ADR-001](backend/docs/adrs/adr-001-jwt-rsa256.md) | RS256 over HS256 (algorithm confusion prevention) |
| [ADR-002](backend/docs/adrs/adr-002-refresh-token-rotation.md) | Opaque refresh tokens + RTR over long-lived JWTs |
| [ADR-003](backend/docs/adrs/adr-003-argon2id-password-hashing.md) | Argon2id + zxcvbn + HIBP over bcrypt |
| [ADR-004](backend/docs/adrs/adr-004-postgresql-rls.md) | PostgreSQL RLS for tenant isolation |
| [ADR-005](backend/docs/adrs/adr-005-redis-permission-cache.md) | Redis permission cache with 5-min TTL |
| [ADR-006](backend/docs/adrs/adr-006-contextvars-workspace-isolation.md) | `contextvars` over thread-local for async safety |
| [ADR-007](backend/docs/adrs/adr-007-sliding-window-rate-limiter.md) | Sliding window over fixed window (no boundary spikes) |
| [ADR-008](backend/docs/adrs/adr-008-oauth-external-idp-framework.md) | OAuth as provider-agnostic framework |

### Authentication sequence diagrams

See [auth-sequence-diagrams.md](backend/docs/auth-sequence-diagrams.md) for
Mermaid sequence diagrams covering:
1. Registration + idempotency
2. Email verification
3. Login + session management
4. Token refresh + RTR replay detection
5. IAM middleware pipeline
6. Google OAuth + CSRF state validation
7. WebSocket handshake authentication

---

## Architectural Overview

```
                      [ Client UI Dashboard (Next.js) ]
                                    |
                                    | WebSockets / HTTP REST
                                    v
                          [ API Gateway / FastAPI ]
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
            v                       v                       v
    [ PostgreSQL + pgvector ]    [ Redis Cache ]     [ MinIO Storage ]
         (RLS enabled)         (permissions +        (meeting recordings
                                rate limiting)        + transcripts)
```

**Frontend**: Next.js App Router (TypeScript, Tailwind CSS, shadcn/ui)  
**Backend**: FastAPI (Python 3.13), SQLAlchemy 2.0, Pydantic v2  
**Database**: PostgreSQL with `pgvector` + Row-Level Security  
**Cache**: Redis (permissions, rate limiting, sessions)  
**Storage**: MinIO (S3-compatible, meeting recordings and transcripts)

---

## Repository Structure

```
noted-maam/
├── .github/workflows/ci.yml    # Automated CI (lint, test, build)
├── backend/
│   ├── app/
│   │   ├── api/                # HTTP endpoints + WebSocket routes
│   │   ├── application/        # Use case coordinators
│   │   ├── core/               # Settings, database, JWKS, IAM, rate limiter
│   │   ├── domain/             # Pure domain entities
│   │   ├── infrastructure/     # Storage and cache adapters
│   │   ├── models/             # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic (IdentityService, etc.)
│   │   └── main.py             # Application factory + middleware stack
│   ├── docs/
│   │   ├── adrs/               # Architecture Decision Records (ADR-001–008)
│   │   └── auth-sequence-diagrams.md
│   ├── tests/
│   │   ├── test_auth.py        # Registration, verification, login, RTR
│   │   ├── test_iam.py         # Middleware, rate limiter, session management
│   │   ├── test_security.py    # JWT forgery, JWKS, OAuth CSRF, WebSocket
│   │   └── test_main.py        # Health, root endpoints
│   ├── alembic/                # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/app/                # Next.js App Router pages
│   └── src/styles/
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## Getting Started

### Prerequisites
- **Docker Engine** v24.0.0+
- **Docker Compose** v2.20.0+
- **Make** (optional but recommended)

### One-command setup

```bash
# 1. Initialize environment files
make setup

# 2. Start all services (DB, Redis, MinIO, backend, frontend)
make dev
```

Once running:
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **JWKS Endpoint**: [http://localhost:8000/api/v1/auth/.well-known/jwks.json](http://localhost:8000/api/v1/auth/.well-known/jwks.json)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001)

---

## Development Operations

### Testing

```bash
# Run all tests with coverage
make test

# Run security tests only
cd backend && .venv/Scripts/python -m pytest tests/test_security.py -v

# Run with coverage report
cd backend && .venv/Scripts/python -m pytest --cov=app --cov-report=html
```

### Linting & Type Checking

```bash
# Ruff (lint + format)
make lint
make format

# mypy strict type checking
cd backend && .venv/Scripts/mypy app
```

---

## Development Guidelines

### Coding Conventions
- **Domain isolation**: never import SQLAlchemy entities into domain logic
- **Strict typing**: all Python must pass `mypy --strict`; all TypeScript must compile clean
- **No hardcoded secrets**: all secrets via `Settings` class → `.env`
- **Test-first for security**: every auth or IAM change requires a corresponding test

### Branching Strategy
- `main`: production-ready releases only
- `develop`: integration branch
- `feature/<name>`: feature branches, must pass CI before PR merge

### Implementation Rule
> No endpoint, model, middleware, service, or frontend component may be
> implemented unless it can be traced back to an approved section of the
> Technical Design Document.

---

## Implementation Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Repository, CI/CD, Docker infrastructure | ✅ Complete |
| Phase 2 | Identity & Access Management | ✅ Complete |
| Phase 2.11 | Frontend auth views (Login, Register, Sessions) | 🔄 In Progress |
| Phase 3 | Meeting Lifecycle & Storage | ⏳ Planned |
| Phase 4 | Streaming Pipeline & WebSocket Ingestion | ⏳ Planned |
| Phase 5 | Speech-to-Text (Whisper) Integration | ⏳ Planned |
| Phase 6 | AI Summarization & Action Item Extraction | ⏳ Planned |
| Phase 7 | Semantic Search (pgvector + RAG) | ⏳ Planned |
| Phase 8 | Enterprise Integrations (Slack, Jira, Calendar) | ⏳ Planned |
| Phase 9 | Production Hardening & Observability | ⏳ Planned |
