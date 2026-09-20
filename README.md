# NOTED MA'AM — Enterprise Meeting Operating System

> *"Meetings End. Work Begins."*

**Noted Ma'am** is a production-grade, AI-native meeting intelligence platform designed to ingest meeting streams, execute diarization, and turn conversations into verified decisions, accountable commitments, and searchable project memory. Built with a sophisticated **Burgundy & Cream** editorial aesthetic and backed by a high-concurrency event-driven architecture.

---

## 🌟 Key Capabilities & Features

- **Outcome-First Meeting Workspace**: Prioritizes deliverables over raw transcripts (Summary → Action Items → Confirmed Decisions → Diarized Transcript). Features exact audio timestamp playback (`[▶ Play Audio XX:YY]`).
- **Human-in-the-Loop Verification Gate**: AI proposes commitments; humans verify before project assignment. Eliminates unverified task drift.
- **Dual Operational Modes**:
  - **Demo Showcase Mode**: Interactive portfolio dataset featuring pre-diarized transcripts, decision version trees, and project pulse logs.
  - **Real-World Production Mode**: Live connection to the FastAPI backend (`http://localhost:8000/api/v1`) with MinIO object storage and PostgreSQL vector memory.
- **Single-Palette & Accent Trust System**: Multi-state badge indicators (`CONFIRMED`, `CONFLICTING`, `UNKNOWN`, `PARTIAL`) utilizing clear red, yellow, and green accents on a warm cream canvas.
- **Deterministic Project Pulse**: Real-time change logs tracking blockers, overdue commitments, and decision supersessions without black-box AI scoring.
- **Searchable Project Memory**: Semantic query RAG powered by `pgvector` with strict hallucination boundaries (`ANSWERABLE`, `CONFLICTING`, `UNKNOWN`).
- **Enterprise-Grade Security & IAM**: RS256 JWT, Refresh Token Rotation (RTR), PostgreSQL Row-Level Security (RLS), and comprehensive audit event streaming.

---

## 🧭 5-Job User Navigation Architecture

1. **Executive Home (`/app/home`)**: Daily operational briefing, items requiring attention, and project pulse summaries.
2. **Meetings & Ingestion Hub (`/app/meetings`)**: Audio recording ingestion (`.wav`, `.mp3`), diarized transcripts, and unassigned inbox management.
3. **Work Center (`/app/work`)**: Verification queue separating AI task proposals from execution states, complete with voiceprint provenance drawers.
4. **Project Intelligence (`/app/projects`)**: Project change detection engine tracking open blockers, overdue commitments, and decision changes.
5. **Knowledge Engine (`/app/knowledge`)**: Interactive decision supersession lineage trees and semantic memory search.

---

## 🏗️ System Architecture

```
                                [ Client UI Dashboard (Next.js 16 + Tailwind) ]
                                                       |
                                            HTTP REST / WebSockets
                                                       v
                                            [ FastAPI API Gateway ]
                                                       |
                    +----------------------------------+----------------------------------+
                    |                                  |                                  |
                    v                                  v                                  v
        [ PostgreSQL + pgvector ]              [ Redis Engine ]                  [ MinIO S3 Store ]
      (RLS + Decision Lineage DB)           (Sessions + Rate Limiter)          (Recordings + Transcripts)
```

| Subsystem | Technologies & Frameworks |
| :--- | :--- |
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS, Lucide Icons, AppMode Context |
| **Backend** | FastAPI (Python 3.13), SQLAlchemy 2.0, Pydantic v2, Pytest (115 tests passing) |
| **Database & Memory** | PostgreSQL 16 with `pgvector` & Row-Level Security (RLS) |
| **Cache & Queue** | Redis 7 (permission caching, rate limiting, sliding window) |
| **Storage** | MinIO S3-compatible audio stream storage |

---

## 🚀 Quick Start Guide

### Prerequisites
- **Node.js** v18+ & **npm**
- **Python** 3.11+ & **pytest**
- **Docker Engine** v24+ & **Docker Compose**

### Running the Application

```bash
# 1. Clone the repository
git clone https://github.com/Tanishka-2004/noted-maam.git
cd noted-maam

# 2. Run Frontend
cd frontend
npm install
npm run dev
```

Visit **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 🧪 Verification & Build Status

```bash
# Run backend domain test suite (115 tests passing)
cd backend
python -m pytest tests/test_knowledge_index.py tests/test_meeting_domain.py tests/test_security.py -v

# Run production build validation (31/31 routes compiling clean)
cd frontend
npm run build
```

---

## 📄 License & Repository

Maintained at: **[https://github.com/Tanishka-2004/noted-maam](https://github.com/Tanishka-2004/noted-maam)**
