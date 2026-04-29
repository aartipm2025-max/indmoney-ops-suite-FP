"""
pillars/pillar_a_knowledge/reranker.py

Cross-encoder reranker: scores query-chunk pairs and returns the top-k.
"""

from __future__ import annotations

from typing import Any

from sentence_transformers import CrossEncoder

from core.logger import log

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_MAX_LENGTH = 256


class CrossEncoderReranker:
    def __init__(self) -> None:
        log.info("CrossEncoderReranker: loading model '{}'", RERANKER_MODEL)
        self.model = CrossEncoder(
            RERANKER_MODEL,
            max_length=RERANK_MAX_LENGTH,
        )
        log.info("CrossEncoderReranker: ready")

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        log.info(
            "CrossEncoderReranker.rerank: query='{}...' candidates={} top_k={}",
            query[:80],
            len(candidates),
            top_k,
        )

        pairs = [(query, c["text"]) for c in candidates]
        scores = self.model.predict(pairs, show_progress_bar=False)

        for candidate, score in zip(candidates, scores):
            candidate["rerank_score"] = float(score)

        reranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
        top = reranked[:top_k]

        log.info(
            "CrossEncoderReranker.rerank: returning {} chunks (top score={:.4f})",
            len(top),
            top[0]["rerank_score"] if top else 0.0,
        )
        return top
