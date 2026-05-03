"""
pillars/pillar_a_knowledge/retriever.py

Hybrid retriever: BM25 (sparse) + ChromaDB (dense) + Reciprocal Rank Fusion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import bm25s
import chromadb
from sentence_transformers import SentenceTransformer

from core.logger import log

COLLECTION_NAME = "sbi_mf_knowledge"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
RRF_K = 60


class HybridRetriever:
    def __init__(
        self,
        chroma_persist_dir: Path,
        bm25_persist_dir: Path,
    ) -> None:
        log.info("HybridRetriever: loading ChromaDB from {}", chroma_persist_dir)
        client = chromadb.PersistentClient(path=str(chroma_persist_dir))
        self.collection = client.get_collection(COLLECTION_NAME)
        log.info(
            "HybridRetriever: collection '{}' loaded ({} docs)",
            COLLECTION_NAME,
            self.collection.count(),
        )

        log.info("HybridRetriever: loading BM25 index from {}", bm25_persist_dir)
        self.bm25 = bm25s.BM25.load(str(bm25_persist_dir), load_corpus=True)
        log.info("HybridRetriever: BM25 index loaded")

        log.info("HybridRetriever: loading embedding model '{}'", EMBEDDING_MODEL)
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        log.info("HybridRetriever: ready")

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        bm25_weight: float = 0.3,
        dense_weight: float = 0.7,
    ) -> list[dict[str, Any]]:
        log.info("HybridRetriever.retrieve: query='{}...' top_k={}", query[:60], top_k)

        bm25_ranked = self._bm25_search(query, top_k)
        dense_ranked = self._dense_search(query, top_k)
        fused = self._rrf(bm25_ranked, dense_ranked, top_k, bm25_weight, dense_weight)

        bm25_rank_map = {doc_id: rank for rank, (doc_id, _) in enumerate(bm25_ranked, 1)}
        dense_rank_map = {doc_id: rank for rank, (doc_id, _) in enumerate(dense_ranked, 1)}

        fused_ids = [doc_id for doc_id, _ in fused]
        if not fused_ids:
            return []

        # Single batched fetch instead of one get() per document
        batch = self.collection.get(
            ids=fused_ids,
            include=["documents", "metadatas"],
        )
        doc_lookup: dict[str, tuple[str, dict]] = {
            did: (batch["documents"][i], batch["metadatas"][i])
            for i, did in enumerate(batch["ids"])
        }

        results: list[dict[str, Any]] = []
        for doc_id, rrf_score in fused:
            if doc_id not in doc_lookup:
                continue
            text, metadata = doc_lookup[doc_id]
            results.append(
                {
                    "doc_id": doc_id,
                    "text": text,
                    "metadata": metadata,
                    "rrf_score": rrf_score,
                    "bm25_rank": bm25_rank_map.get(doc_id),
                    "dense_rank": dense_rank_map.get(doc_id),
                }
            )

        log.info("HybridRetriever.retrieve: returning {} chunks", len(results))
        return results

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _bm25_search(
        self, query: str, top_k: int
    ) -> list[tuple[str, float]]:
        tokens = bm25s.tokenize([query], show_progress=False)
        raw_results, raw_scores = self.bm25.retrieve(
            tokens, k=top_k, show_progress=False
        )
        # raw_results[0] is a list of corpus dicts; raw_scores[0] is floats
        ranked: list[tuple[str, float]] = []
        for item, score in zip(raw_results[0], raw_scores[0]):
            doc_id = item["doc_id"] if isinstance(item, dict) else str(item)
            ranked.append((doc_id, float(score)))
        return ranked

    def _dense_search(
        self, query: str, top_k: int
    ) -> list[tuple[str, float]]:
        embedding = self.embedding_model.encode(
            [query], normalize_embeddings=True
        )
        chroma_res = self.collection.query(
            query_embeddings=embedding.tolist(),
            n_results=top_k,
            include=["distances"],
        )
        # distances are cosine distances; convert to similarity
        ranked: list[tuple[str, float]] = []
        for doc_id, dist in zip(
            chroma_res["ids"][0], chroma_res["distances"][0]
        ):
            ranked.append((doc_id, 1.0 - float(dist)))
        return ranked

    @staticmethod
    def _rrf(
        bm25_ranked: list[tuple[str, float]],
        dense_ranked: list[tuple[str, float]],
        top_k: int,
        bm25_weight: float,
        dense_weight: float,
    ) -> list[tuple[str, float]]:
        bm25_rank_map = {
            doc_id: rank for rank, (doc_id, _) in enumerate(bm25_ranked, 1)
        }
        dense_rank_map = {
            doc_id: rank for rank, (doc_id, _) in enumerate(dense_ranked, 1)
        }

        all_ids = set(bm25_rank_map) | set(dense_rank_map)
        scores: dict[str, float] = {}
        for doc_id in all_ids:
            score = 0.0
            if doc_id in bm25_rank_map:
                score += bm25_weight * (1.0 / (RRF_K + bm25_rank_map[doc_id]))
            if doc_id in dense_rank_map:
                score += dense_weight * (1.0 / (RRF_K + dense_rank_map[doc_id]))
            scores[doc_id] = score

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
