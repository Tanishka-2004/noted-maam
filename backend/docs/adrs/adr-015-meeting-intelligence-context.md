# ADR-015: Meeting Intelligence Bounded Context & Staged Validation

**Status**: Accepted  
**Date**: 2026-07-10  
**Category**: Domain Architecture  
**Deciders**: Engineering Lead  

## Context

Following the generation of transcription data (Phase 5), the system needs to extract organizational knowledge (summaries, action items, decisions, conflicts, follow-ups). 

Key challenges:
1. LLM output can be non-deterministic, unstructured, or hallucinated.
2. Artifacts must maintain evidence linking back to the source transcript utterances.
3. Artifacts must carry multi-dimensional confidence scores to gate human review states.

## Decision

We introduce a dedicated **Meeting Intelligence Bounded Context** that isolates LLM execution behind an adapter interface and processes extraction via a linear **Staged Verification Pipeline**.

### Key Rules
- **Unified Artifact Store**: All extracted artifacts (Summary, ActionItem, Decision, Conflict, Followup) extend a common schema providing review status (`Draft`, `Validated`, `NeedsReview`, `Approved`, `Published`), evidence links (`source_utterance_ids`), and multi-dimensional confidence scores.
- **Staged Verification Pipeline**:
  1. Context Builder: Assembles transcript and participants metadata.
  2. Prompt Router: Prepares JSON schemas and model prompts.
  3. LLM Engine Adapter: Executes model inference.
  4. Grounding Validator: Verifies cited utterance IDs actually exist in the database (rejecting hallucinations).
  5. Confidence Gating: Overall confidence < 0.8 flags items as `NeedsReview`.
- **Model Isolation**: Core domain entities have zero direct dependencies on external LLM clients. The `MeetingIntelligenceEngine` interface abstracts the provider, backed by a configurable environment variable (`mock` or `gemini`).

## Alternatives Considered

1. **Direct LLM execution inside endpoints**: Rejected because processing takes seconds/minutes and must run asynchronously.
2. **Ad-hoc artifact schemas**: Rejected because lack of uniform review states and evidence tracking would prevent robust UI integration and auditing.

## Consequences

- Tests remain deterministic using the mock engine.
- Citations guarantee traceability for auditing and human validation.
- Swapping models (Gemini to Claude/Local Llama) requires only writing a concrete adapter class.
