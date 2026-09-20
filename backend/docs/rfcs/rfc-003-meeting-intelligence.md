# RFC-003: Meeting Intelligence Bounded Context

This RFC defines the architectural boundaries, domain model, LLM orchestration strategy, staged verification pipeline, evidence model, and quality assurance framework for the **Meeting Intelligence Context** within the **Noted Ma'am** Meeting Operating System.

---

## 1. Context Boundaries & Responsibilities

The Meeting Intelligence Context is a dedicated downstream consumer that transforms structured transcripts into organizational knowledge artifacts. It is the **only** context that orchestrates LLM inference.

```
[Speech Processing Context]
          │
          │ (TranscriptReady Event)
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Meeting Intelligence Context                                               │
│                                                                             │
│  [TranscriptReady Consumer]                                                │
│          │                                                                  │
│          └──> [Staged Verification Pipeline]                                │
│                   │                                                         │
│                   ├──> Context Builder                                      │
│                   ├──> Prompt Router & LLM Adapter                          │
│                   ├──> Schema & Grounding Validator                         │
│                   ├──> Confidence Scorer & Human Review Gate                │
│                   ▼                                                         │
│               [Artifact Store]                                              │
│                   ├──> Summary Generated         ──> SummaryGenerated       │
│                   ├──> Action Items Extracted    ──> ActionItemsExtracted   │
│                   ├──> Decisions Captured        ──> DecisionsCaptured      │
│                   ├──> Conflicts Detected        ──> ConflictsDetected      │
│                   └──> Follow-ups Generated      ──> FollowupsGenerated     │
│                                                                             │
│                       ──> IntelligenceValidated                             │
│                       ──> MeetingIntelligenceReady                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    [Search / RAG Context]
                    [Analytics Context]
                    [Integrations Context]
```

### Core Invariants

1. **No direct transcript mutation**: Intelligence artifacts reference transcript spans but never modify utterance, word, or speaker identity data.
2. **Grounding requirement**: Every extracted insight (action item, decision, conflict, follow-up) MUST cite the source utterance IDs that produced it via a structured Evidence Model.
3. **Confidence gating**: Extracted items below a configurable confidence threshold or having low grounding quality are flagged for human review.
4. **LLM isolation**: The Meeting and Speech contexts have zero knowledge of LLM providers. Only this context imports LLM client libraries.
5. **Idempotency**: Re-processing the same transcript version produces deterministic intelligence artifacts.

---

## 2. Domain Model & Artifact Store

Rather than storing intelligence outputs ad hoc, all generated outputs are treated as explicit entities within an unified **Artifact Store** sharing common traits.

### 2.1 The Evidence Model

Every AI-generated intelligence artifact carries a common provenance structure ensuring strict traceability:

```json
{
  "id": "uuid",
  "type": "action_item",
  "source_utterance_ids": [
    "utt_143",
    "utt_144"
  ],
  "source_word_ranges": [
    [1204, 1218]
  ],
  "model_provider": "mock",
  "model_version": "v1.0",
  "verification_status": "grounded",
  "created_at": "2026-07-10T14:16:35Z"
}
```

### 2.2 Multi-Dimensional Confidence

Instead of a single scalar confidence score, each artifact records multi-dimensional confidence:

- **Extraction Confidence**: Probability that the candidate item is a valid target (e.g. is truly a task or decision).
- **Ownership Confidence**: Confidence in the speaker-to-participant mapping or assignee extraction.
- **Temporal Confidence**: Reliability of the deadline or timeline parsed.
- **Grounding Confidence**: Extent of alignment between the generated text and the cited transcript evidence source.
- **Overall Confidence**: Aggregated score determining downstream automation vs. human gating.

### 2.3 Artifact Definitions

#### Summary (`meeting_summaries`)
- **Executive Summary**: 2-3 sentence high-level overview.
- **Key Topics**: Key topic headings with local summaries and evidence chains.
- **Outcomes**: Decisive deliverables accomplished.
- **Open Questions**: Unresolved issues needing future meetings.

#### Action Item (`action_items`)
- **Title & Description**: Measurable outcome and task detail.
- **Assignee**: Owner name or speaker tag.
- **Priority**: High, Medium, Low.
- **Deadline**: Raw text and parsed date (if extractable).

#### Decision (`decisions`)
- **Summary**: Concise statement of agreed direction.
- **Context & Rationale**: What was discussed and why this option was chosen.
- **Participants Involved**: Explicit list of participants participating in the consensus.

#### Conflict (`conflicts`)
- **Topic**: Summary of disagreement.
- **Positions**: Opposing stances mapped to individual speaker tags and evidence.
- **Resolution Status**: Resolved, Unresolved, or Deferred.

#### Follow-up (`followups`)
- **Description**: Actionable next step.
- **Suggested Date**: Targeted calendar date.
- **Related Action Item ID**: Option pointer back to an extracted Action Item.

---

## 3. Staged Verification Pipeline

Before any intelligence artifact is persisted to the database or broadcasted to other services, it must pass through a linear verification pipeline:

```
TranscriptReady
   │
   ▼
[Context Builder]         — Gathers transcript, speaker identities, participant list.
   │
   ▼
[Prompt Router]          — Generates structured prompts for specific LLM configuration.
   │
   ▼
[LLM Adapter (Engine)]    — Executes model inference (Gemini, Llama, Mock).
   │
   ▼
[JSON Schema Validation]  — Enforces structured output format and type safety.
   │
   ▼
[Grounding Validator]    — Cross-checks cited source_utterance_ids against original transcript content to catch hallucinations.
   │
   ▼
[Confidence Scorer]      — Rates extraction, ownership, and grounding dimensions.
   │
   ▼
[Human Review Gate]      — Flags low-confidence items with `requires_review = True`.
   │
   ▼
[Persist & Publish]      — Commits artifacts to DB outbox, dispatches events.
```

---

## 4. LLM Provider Adapter Strategy

All model execution runs through the abstract `MeetingIntelligenceEngine` interface. Concrete providers are configured dynamically via settings:

```python
class MeetingIntelligenceEngine(ABC):
    @abstractmethod
    def process_transcript(
        self, 
        transcript_text: str, 
        utterances: List[dict]
    ) -> Dict[str, Any]:
        """Runs the entire intelligence extraction pipeline returning structured raw artifacts."""
        pass
```

### Supported Providers
1. **MockIntelligenceEngine** (Default): Deterministic provider returning canned grounded responses. Essential for unit tests, offline development, and zero-key builds.
2. **GeminiIntelligenceEngine**: Production provider utilizing Google's Gemini API via structured schemas.

---

## 5. Event Flow

```
TranscriptReady
   │
   ▼ (Intelligence Worker starts)
IntelligenceStarted
   │
   ├──> SummaryGenerated
   ├──> ActionItemsExtracted
   ├──> DecisionsCaptured
   ├──> ConflictsDetected
   │
   ▼ (After pipeline checks pass)
IntelligenceValidated
   │
   ▼
MeetingIntelligenceReady
```
