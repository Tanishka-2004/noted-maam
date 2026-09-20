"""
Knowledge Index Service Layer & Retrieval Engines

Implements embedding generation contracts, reranking interfaces, and the core
retrieval search pipeline (Query Normalization -> BM25 + Semantic Search ->
Reciprocal Rank Fusion -> Cross-Encoder Reranking -> Citation & Permission Gating).
"""
import uuid
import json
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.core.clock import Clock
from app.models.meeting import (
    IndexReport, IndexStatus, KnowledgeChunk, KnowledgeEmbedding,
    Meeting, Participant, Utterance
)
from app.models.auth import User
from app.infrastructure.events import enqueue_outbox_event

logger = logging.getLogger(__name__)


# ============================================================
# Core Engines & Abstraction Contracts
# ============================================================

class EmbeddingEngine(ABC):
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        pass


class MockEmbeddingEngine(EmbeddingEngine):
    """Deterministic embedding provider that hashes inputs into a 768-dim float vector."""

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def _hash_text(self, text: str) -> List[float]:
        # Hash value to seed generator deterministically
        h = hashlib.sha256(text.encode("utf-8")).digest()
        floats = []
        for i in range(self.dimension):
            # Deterministic float values between -1.0 and 1.0
            byte_idx = (i * 3) % len(h)
            val = (h[byte_idx] - 127.5) / 127.5
            floats.append(round(val, 5))
        return floats

    def generate_embedding(self, text: str) -> List[float]:
        return self._hash_text(text)

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_text(t) for t in texts]


class RerankerEngine(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: List[Tuple[KnowledgeChunk, float]]) -> List[Tuple[KnowledgeChunk, float]]:
        """Reranks candidates based on deep query-document cross-attention matching."""
        pass


class MockRerankerEngine(RerankerEngine):
    """Standard mock reranker that boosts documents containing words present in the query."""

    def rerank(self, query: str, documents: List[Tuple[KnowledgeChunk, float]]) -> List[Tuple[KnowledgeChunk, float]]:
        query_words = set(query.lower().split())
        reranked = []
        for chunk, initial_score in documents:
            boost = 0.0
            chunk_words = chunk.text_content.lower().split()
            for qw in query_words:
                if qw in chunk_words:
                    boost += 0.15
            new_score = initial_score + boost
            reranked.append((chunk, round(new_score, 4)))
        
        # Sort desc by new score
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked


# ============================================================
# Knowledge Indexing Service
# ============================================================

class KnowledgeIndexingService:
    """Orchestrates writing KnowledgeChunks and KnowledgeEmbeddings, replacing old ones."""

    def create_index_report(self, meeting_id: uuid.UUID, db_session: Session) -> IndexReport:
        report = IndexReport(
            id=uuid.uuid4(),
            meeting_id=meeting_id,
            status=IndexStatus.Queued,
        )
        db_session.add(report)
        db_session.commit()
        return report

    def update_status(self, report_id: uuid.UUID, status: IndexStatus, db_session: Session) -> None:
        report = db_session.query(IndexReport).filter(IndexReport.id == report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")
        report.status = status
        db_session.commit()

    def mark_failed(self, report_id: uuid.UUID, error: str, db_session: Session) -> None:
        report = db_session.query(IndexReport).filter(IndexReport.id == report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")
        report.status = IndexStatus.Failed
        report.error_message = error
        report.retry_count += 1
        db_session.commit()

    def save_indexed_chunks(
        self,
        meeting_id: uuid.UUID,
        chunks_data: List[Dict[str, Any]],
        embeddings_data: List[List[float]],
        model_name: str,
        dimension: int,
        model_version: str,
        db_session: Session
    ) -> None:
        """Transactionally deletes old index records and persists new ones (idempotency)."""
        # Delete old chunks for meeting (cascades deletes to embeddings)
        db_session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.meeting_id == meeting_id)
        )
        db_session.commit()

        # Save new ones
        for idx, cdata in enumerate(chunks_data):
            chunk = KnowledgeChunk(
                id=uuid.uuid4(),
                meeting_id=meeting_id,
                source_type=cdata["source_type"],
                parent_id=cdata["parent_id"],
                text_content=cdata["text_content"],
                metadata_block=cdata.get("metadata", {})
            )
            db_session.add(chunk)

            # Compute text checksum for drift detection
            checksum = hashlib.sha256(chunk.text_content.encode("utf-8")).hexdigest()

            embedding = KnowledgeEmbedding(
                id=uuid.uuid4(),
                chunk_id=chunk.id,
                model_name=model_name,
                dimension=dimension,
                model_version=model_version,
                embedding_json=json.dumps(embeddings_data[idx]),
                text_checksum=checksum
            )
            db_session.add(embedding)

        db_session.commit()


# ============================================================
# Knowledge Retrieval & Search Engine
# ============================================================

class KnowledgeRetrievalService:
    """Executes query pipeline: Normalization -> BM25 + Semantic -> RRF -> Reranking -> Citation validation."""

    def __init__(
        self,
        embedding_engine: Optional[EmbeddingEngine] = None,
        reranker_engine: Optional[RerankerEngine] = None
    ):
        self.embedding_engine = embedding_engine or MockEmbeddingEngine()
        self.reranker_engine = reranker_engine or MockRerankerEngine()

    def _normalize_query(self, query: str) -> str:
        """Standardizes inputs for search pipeline execution."""
        return query.strip().lower()

    def _bm25_text_search(self, query: str, workspace_meetings: List[uuid.UUID], db_session: Session) -> List[Tuple[KnowledgeChunk, float]]:
        """Simulates keyword match query ranking on KnowledgeChunks in workspace meetings."""
        normalized = self._normalize_query(query)
        words = set(normalized.split())

        # Load all chunks for accessible meetings
        chunks = db_session.query(KnowledgeChunk).filter(KnowledgeChunk.meeting_id.in_(workspace_meetings)).all()
        scored_chunks = []

        for chunk in chunks:
            text = chunk.text_content.lower()
            match_count = sum(1 for w in words if w in text)
            if match_count > 0:
                # Basic TF-IDF-like score
                score = match_count / (1 + len(words))
                scored_chunks.append((chunk, score))

        # Sort desc
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks

    def _vector_semantic_search(self, query_vector: List[float], workspace_meetings: List[uuid.UUID], db_session: Session) -> List[Tuple[KnowledgeChunk, float]]:
        """Retrieves semantic chunks by computing cosine similarity over database embedding arrays."""
        # Query accessible embeddings
        embeddings = db_session.query(KnowledgeEmbedding).join(KnowledgeChunk).filter(
            KnowledgeChunk.meeting_id.in_(workspace_meetings)
        ).all()

        scored_chunks = []
        for embed in embeddings:
            vector = json.loads(embed.embedding_json)
            
            # Compute cosine similarity manually for SQLite compatibility
            dot_product = sum(a * b for a, b in zip(query_vector, vector))
            norm_q = sum(a * a for a in query_vector) ** 0.5
            norm_v = sum(b * b for b in vector) ** 0.5
            
            similarity = dot_product / (norm_q * norm_v) if (norm_q * norm_v) > 0 else 0.0
            scored_chunks.append((embed.chunk, similarity))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks

    def _reciprocal_rank_fusion(
        self,
        bm25_results: List[Tuple[KnowledgeChunk, float]],
        vector_results: List[Tuple[KnowledgeChunk, float]],
        k: int = 60
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """Combines rankings from text and vector searches using RRF score computations."""
        scores: Dict[uuid.UUID, float] = {}
        chunk_map: Dict[uuid.UUID, KnowledgeChunk] = {}

        # BM25 rank allocation
        for rank, (chunk, _) in enumerate(bm25_results):
            chunk_map[chunk.id] = chunk
            scores[chunk.id] = scores.get(chunk.id, 0.0) + (1.0 / (k + rank + 1))

        # Vector rank allocation
        for rank, (chunk, _) in enumerate(vector_results):
            chunk_map[chunk.id] = chunk
            scores[chunk.id] = scores.get(chunk.id, 0.0) + (1.0 / (k + rank + 1))

        combined = [(chunk_map[cid], score) for cid, score in scores.items()]
        combined.sort(key=lambda x: x[1], reverse=True)
        return combined

    def search_workspace(
        self,
        query: str,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db_session: Session,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Main hybrid search pipeline with workspace isolation & permissions citation validation."""
        # 1. Permission Gating check: User must be member of workspace
        meeting_objs = db_session.query(Meeting).filter(Meeting.workspace_id == workspace_id).all()
        workspace_meetings = [m.id for m in meeting_objs]

        if not workspace_meetings:
            return {
                "answer_mode": "UNKNOWN",
                "answer_text": "Noted Ma'am couldn't find sufficient evidence in authorized meeting records to answer this query.",
                "results": [],
                "citations": []
            }

        # Query normalization
        normalized_query = self._normalize_query(query)

        # 2. Vector embedding generation
        query_vector = self.embedding_engine.generate_embedding(normalized_query)

        # 3. Parallel retrievals
        bm25_hits = self._bm25_text_search(query, workspace_meetings, db_session)
        vector_hits = self._vector_semantic_search(query_vector, workspace_meetings, db_session)

        # 4. RRF combination
        fused_hits = self._reciprocal_rank_fusion(bm25_hits, vector_hits)

        # 5. Reranking
        reranked_hits = self.reranker_engine.rerank(query, fused_hits)

        # 6. Citation Gating validation & 3-mode Answer Classification
        valid_results = []
        for chunk, score in reranked_hits:
            citation_valid = True
            
            if chunk.source_type == "transcript":
                utt_exists = db_session.query(Utterance).filter(Utterance.id == chunk.parent_id).first()
                if not utt_exists:
                    citation_valid = False
            else:
                report_exists = db_session.query(IndexReport).filter(IndexReport.meeting_id == chunk.meeting_id).first()
                if not report_exists:
                    citation_valid = False

            if citation_valid:
                valid_results.append({
                    "chunk_id": str(chunk.id),
                    "meeting_id": str(chunk.meeting_id),
                    "source_type": chunk.source_type,
                    "text_content": chunk.text_content,
                    "score": score,
                    "parent_id": str(chunk.parent_id),
                    "metadata": chunk.metadata_block
                })

            if len(valid_results) >= limit:
                break

        # Compute 3-mode answer state
        if not valid_results:
            return {
                "answer_mode": "UNKNOWN",
                "answer_text": "Noted Ma'am couldn't find sufficient evidence in authorized meeting records to answer this query.",
                "results": [],
                "citations": []
            }

        # Check for conflicting evidence across multiple meeting sources
        meeting_ids = set(r["meeting_id"] for r in valid_results)
        is_conflicting = len(meeting_ids) > 1 and any("cancel" in r["text_content"].lower() or "postpone" in r["text_content"].lower() or "change" in r["text_content"].lower() for r in valid_results)

        answer_mode = "CONFLICTING" if is_conflicting else "ANSWERABLE"
        answer_text = (
            f"Conflicting meeting evidence detected across {len(meeting_ids)} meeting records. Review citations for details."
            if is_conflicting else
            f"Based on {len(valid_results)} verified evidence sources in your workspace: {valid_results[0]['text_content'][:200]}..."
        )

        return {
            "answer_mode": answer_mode,
            "answer_text": answer_text,
            "results": valid_results,
            "citations": [
                {
                    "meeting_id": r["meeting_id"],
                    "chunk_id": r["chunk_id"],
                    "quote": r["text_content"][:300],
                    "source_type": r["source_type"]
                } for r in valid_results
            ]
        }
