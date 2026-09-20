# ADR-016: Knowledge Index Bounded Context & Hybrid Retrieval

**Status**: Accepted  
**Date**: 2026-07-10  
**Category**: Domain Architecture  
**Deciders**: Engineering Lead  

## Context

Following the extraction of structured meeting intelligence artifacts (Phase 6), the system needs to partition, embed, and retrieve knowledge (transcripts and artifacts) semantically to support Q&A and RAG downstream.

Key challenges:
1. Embeddings must be versioned to avoid destructive migrations when upgrading models.
2. Search must merge conceptual (semantic) matching and exact word matching (BM25) to maintain precision.
3. Search results must enforce permission gating and citation validity checks.

## Decision

We introduce a dedicated **Knowledge Index Bounded Context** that isolates vector storage and retrieval.

### Key Rules
- **Hierarchical Chunks**: Continguous transcript utterances are grouped into ~15 utterance blocks (overlapping by 3) to keep context coherent. Artifacts are indexed as individual chunks. Chunks use immutable IDs.
- **Embedding Versioning**: Records specify model names, versions, dimension lengths, and text checksums.
- **Hybrid Retrieval Pipeline**: Search utilizes query normalization -> parallel BM25 and semantic lookups -> reciprocal rank fusion (RRF) -> Cross-Encoder reranking.
- **Citation Validation**: Matches workspace access permissions and verifies parent source entities still exist in primary DB (filtering out deleted or stale records).

## Alternatives Considered

1. **Direct keyword search**: Low semantic recall for conceptual Q&A.
2. **Coupling indexer into Meeting Intelligence**: Violates separation of concerns, complicating embedding model upgrades.

## Consequences

- Mock providers maintain deterministic test executions.
- Changing vector engines or embedding configurations requires only implementing a concrete adapter class.
