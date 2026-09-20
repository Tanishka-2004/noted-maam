# Product Requirement Document (PRD)
## Noted Ma'am — Enterprise Meeting Operating System

> **Tagline**: *"Meetings End. Work Begins."*  
> **Document Version**: 2.1.0  
> **Status**: Approved & Fully Implemented  
> **Target Audience**: Product Management, Engineering Leads, Executive Stakeholders  

---

## 1. Executive Summary & Product Thesis

### 1.1 Problem Statement
Existing AI meeting software functions primarily as transcription dumps and basic text summarizers. They fail at work execution because:
1. **No Accountability Gate**: Unverified AI extracts flood task trackers with incorrect action items.
2. **No Decision Lineage**: Decisions made in past meetings disappear into linear transcripts without version history or supersession tracking.
3. **No Project Pulse**: Teams cannot answer *"What changed since last week?"* without manually listening to hours of recordings.
4. **Black-Box AI Scores**: Generic health scores provide no actionable transparency.

### 1.2 Product Thesis
**Noted Ma'am** is an AI-native meeting operating system that turns conversations into **verified decisions, accountable commitments, and searchable project memory**.

### 1.3 The 6-Part Operational Loop
1. **Capture**: Stream or upload multilingual meeting recordings (`.wav`, `.mp3`) directly into MinIO object storage.
2. **Understand**: Diarize speakers, extract transcript segments, and detect proposed action items and decision candidates.
3. **Verify**: Apply strict human-in-the-loop verification gates (*"AI proposes, humans decide"*).
4. **Execute**: Sync confirmed commitments directly to project task managers (Jira, Linear, Slack).
5. **Remember**: Index speaker utterances and decision versions into PostgreSQL vector memory (`pgvector`).
6. **Detect Change**: Compute deterministic project pulse counters (Blockers, Overdue Commitments, Supersessions) with zero black-box AI scores.

---

## 2. Target Personas & Primary Use Cases

### 2.1 Target Personas
- **Executive & Group PM**: Requires daily operational briefings, project health pulse, and decision lineage tracking.
- **Engineering Lead**: Demands explicit commitment ownership (*Who committed to what, by when, and why*) with direct audio transcript proof.
- **Compliance & Security Officer**: Mandates tenant isolation (PostgreSQL RLS), explicit participant consent, and immutable audit logs.

### 2.2 Core Use Cases
1. **Executive Daily Briefing**: *"What 3 things require my operational attention today?"*
2. **Outcome-First Meeting Review**: Summary → Action Items → Confirmed Decisions → Diarized Transcript (Secondary).
3. **Decision Lineage Investigation**: *"Why did we move the target release date to October 19th?"*
4. **Zero-Hallucination Semantic Memory Search**: 3-mode answers (`ANSWERABLE`, `CONFLICTING`, `UNKNOWN`) with direct audio quotes.

---

## 3. Visual Identity & Design System Requirements

### 3.1 Editorial Aesthetic
The UI enforces an **editorial, warm, sophisticated, and vintage-inspired** B2B aesthetic, avoiding generic dark AI SaaS clichés.

### 3.2 Core Color Palette Tokens

| Token Role | Hex Code | Application in Product |
| :--- | :--- | :--- |
| **Soft Cream** | `#FBF8F1` | Core page canvas background (`bg-[#FBF8F1]`) |
| **Warm Cream** | `#F7F1E5` | Structural containers, cards, and elevated panels (`bg-[#F7F1E5]`) |
| **Dark Cream / Beige** | `#E9DFCE` | Active selection states, drawer backgrounds, and secondary fills |
| **Muted Beige** | `#CDBEA9` | Structural panel borders and outline frames (`border-[#CDBEA9]`) |
| **Deep Burgundy** | `#4A1724` | Primary high-contrast typography and headers (`text-[#4A1724]`) |
| **Primary Burgundy** | `#681F32` | Interactive action buttons, active navigation, and primary badges |
| **Rich Burgundy** | `#7A2940` | Hover states, active tab highlights, and secondary controls |
| **Muted Burgundy** | `#96546A` | Subtitle metadata, muted labels, and secondary borders |

### 3.3 Status Indicator & Trust Badge System

State is communicated using **contrast, fill, border, and clear visual color accents**:

* 🟢 **CONFIRMED** (*Human verified*):
  `bg-emerald-100 text-emerald-950 border-emerald-400` with solid checkmark.
* 🟡 **CONFLICTING** (*Divergence detected*):
  `bg-amber-100 text-amber-950 border-amber-400` with warning triangle icon.
* 🔴 **PARTIAL / Overdue** (*Processing incomplete*):
  `bg-rose-100 text-rose-950 border-rose-400` with alert circle icon.
* ⚪ **UNKNOWN** (*Insufficient evidence*):
  `bg-[#E9DFCE] text-[#4A1724] border-[#CDBEA9]` with help icon.

---

## 4. Information Architecture & 5 Primary User Jobs

The application interface is organized around **5 Primary User Jobs**:

```
                                  [ Noted Ma'am Navigation ]
                                               |
       +-------------------+-------------------+-------------------+-------------------+
       |                   |                   |                   |                   |
       v                   v                   v                   v                   v
   [ 1. Home ]       [ 2. Meetings ]      [ 3. Work ]        [ 4. Projects ]    [ 5. Knowledge ]
Executive Briefing   Ingestion Hub &    Action Center &    Pulse & Change Log   Decision Lineage
& Daily Attention    Outcome Workspace   Verification Gate  & Health Counters    & Vector Search
```

### 4.1 Executive Home (`/app/home`)
- **Daily Executive Briefing**: Action-oriented greeting (*"Good morning, Tanishka. 3 things require your operational attention today"*).
- **Needs Attention Today**: Quick-action list linking directly to verification queues or decision conflicts.
- **Project Pulse Summary**: High-level status cards for active projects.
- **Today's Schedule**: Meeting timeline indicating processed vs upcoming sessions.

### 4.2 Meetings & Ingestion Hub (`/app/meetings`)
- **Unassigned Ingestion Inbox**: Upload audio files (`.wav`, `.mp3`) first; assign to primary projects anytime.
- **Outcome-First Workspace (`/app/meetings/[id]`)**:
  - **Section 1 (Summary)**: High-level narrative of what transpired.
  - **Section 2 (Action Items)**: Proposed commitments with human confirmation gates.
  - **Section 3 (Decisions)**: Verified decisions with evidence quotes.
  - **Section 4 (Transcript)**: Diarized transcript stream with time-seek controls (`[▶ Play Audio XX:YY]`).

### 4.3 Work Center (`/app/work`)
- **State Machine Separation**:
  - **Verification State**: `SUGGESTED` (AI proposal) vs `CONFIRMED` (Human verified).
  - **Execution State**: `OPEN` → `IN_PROGRESS` → `COMPLETED`.
- **Voiceprint Provenance Drawer ("Why am I seeing this?")**: Slide-out inspector displaying exact speaker quote, time range, model version (`whisper-v3`), extractor version (`actions-v3.1`), and confidence score.

### 4.4 Project Intelligence (`/app/projects`)
- **Project Directory & Pulse (`/app/projects/[id]/pulse`)**:
  - **Deterministic Health Counters**: Open Blockers, Overdue Commitments, Unresolved Speaker Conflicts, Decision Changes. Zero black-box scores.
  - **Project Change Log**: Audit event stream answering *"What changed since last week?"*.

### 4.5 Knowledge Engine (`/app/knowledge`)
- **Decision Lineage Tree**: Interactive version history tracking supersession states (`PROPOSED` → `DISCUSSED` → `CONFIRMED` → `ACTIVE` → `SUPERSEDED` → `REVERSED`).
- **Searchable Project Memory**: Semantic query engine powered by `pgvector` with strict hallucination boundaries (`ANSWERABLE`, `CONFLICTING`, `UNKNOWN`).

---

## 5. Dual Operational Mode System

To serve both stakeholder demonstrations and real-world enterprise deployment, the system natively implements **2 operational modes**:

```
                       [ Top Banner Mode Switcher (DemoModeBanner) ]
                                            |
                    +-----------------------+-----------------------+
                    |                                               |
                    v                                               v
        [ 🎭 DEMO SHOWCASE MODE ]                       [ ⚡ REAL-WORLD MODE ]
     Pre-loaded portfolio dataset                   Connected to FastAPI (`localhost:8000`)
     (Project Alpha, sample quotes)                 Real audio ingestion & live DB queries
```

1. **Demo Showcase Mode (`DEMO`)**:
   - Renders rich sample dataset (*Q3 Engineering Architecture Sync*, *Project Alpha*, pre-diarized utterances, decision lineage tree).
   - Designed for portfolio walkthroughs and stakeholder pitches.
2. **Real-World Production Mode (`REAL`)**:
   - Connects to live FastAPI backend at `http://localhost:8000/api/v1`.
   - Starts with a clean production state when unpopulated, featuring clear call-to-actions (**`[Upload Recording to Live Database]`**, **`[Initialize First Project]`**).
   - Enables real audio file ingestion, live vector searches, and actual database task confirmations.
3. **Persistence**: User selection is saved in `localStorage` and persists across all page navigations.

---

## 6. Functional & Technical Specifications

### 6.1 IAM Subsystem Architecture
- **Token Signing**: RS256 asymmetric JWT with JWKS public key rotation (`/api/v1/auth/.well-known/jwks.json`).
- **Session Security**: Opaque refresh token rotation (RTR) with family revocation on replay detection.
- **Tenant Isolation**: PostgreSQL Row-Level Security (RLS) context bound via async `contextvars`.
- **Rate Limiting**: Redis-backed sliding window rate limiter (IP: 100 req/min, User: 20 req/min).

### 6.2 Data Models & Invariants
- **Meeting Aggregate**:
  - `primary_project_id` nullable (supports Unassigned Inbox).
  - State machine: `Scheduled` → `Waiting` → `Recording` → `Ended` → `Processing` → `Ready` (or `Partial`).
- **ActionItem Aggregate**:
  - Direct `project_id` ownership (commitments persist beyond meeting lifecycle).
  - Verification state split (`SUGGESTED` vs `CONFIRMED`).
- **Decision Lineage Aggregate**:
  - Tracks `DecisionEvidence` (speaker, timestamp, audio quote) and `DecisionVersion` supersessions.

### 6.3 Non-Functional Requirements
- **Performance**: API P95 latency < 150ms; static frontend page generation in < 1.5s.
- **Stream Ingestion**: Supports streaming WAV uploads up to 500MB with RIFF magic byte checksum validation.
- **Non-Hallucination Guardrail**: Returns `UNKNOWN` with zero guesses when evidence confidence falls below threshold.

---

## 7. Verification & Build Metrics

- **Backend Pytest Suite**: **115 / 115 tests passing** (`pytest tests/test_knowledge_index.py tests/test_meeting_domain.py tests/test_security.py`).
- **Frontend Build Validation**: **31 / 31 Next.js static & dynamic routes compiled with 0 errors** (`npm run build`).
- **Automated Browser Audit**: Headless browser subagent verified live mode switching, computed styling, and route resolution across all 5 job pages.

---

## 8. Repository & Deployment References

- **GitHub Repository**: [https://github.com/Tanishka-2004/noted-maam](https://github.com/Tanishka-2004/noted-maam)
- **Primary Specifications**:
  - [**README.md**](README.md)
  - [**Walkthrough**](walkthrough.md)
  - [**UI Design Specification**](ui_design_specification.md)
  - [**Implementation Plan**](implementation_plan.md)
