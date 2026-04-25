"""
pillars/pillar_a_knowledge/answerer.py

Phase 3 — LLM answer generation: Instructor + RAGAnswer schema.
"""

from __future__ import annotations

import math
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, conlist

from core.instructor_clients import get_instructor_primary
from core.logger import log
from pillars.pillar_a_knowledge.reranker import CrossEncoderReranker
from pillars.pillar_a_knowledge.retriever import HybridRetriever
from pillars.pillar_a_knowledge.router import route_query
from schemas.rag import Bullet, Citation, DocType, QueryRoute, RAGAnswer

_MODEL = "llama-3.3-70b-versatile"
_REFUSAL_MSG = (
    "I can only provide factual information from official sources. "
    "I cannot give investment advice, recommendations, or personal data."
)
_EDUCATIONAL_LINK = "https://www.amfiindia.com/investor/knowledge-center-info"

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_CHROMA_DIR = _PROJECT_ROOT / "data" / "chroma_db"
_BM25_DIR = _PROJECT_ROOT / "data" / "bm25_index"

_SYS_PROMPT = """\
You are a factual mutual fund information assistant for SBI Mutual Fund products.

RULES — all mandatory, no exceptions:
1. Answer ONLY from the CONTEXT PASSAGES provided. Do not use training knowledge.
2. Never recommend buying, selling, or holding any fund.
3. Never state or imply projected returns or guaranteed performance.
4. Never request or repeat PAN, Aadhaar, bank account, or contact details.
5. Do not speculate about future NAV, returns, or market conditions.
6. Each bullet text MUST contain at least one inline citation in the EXACT format [source:<doc_id>].
   Example: "The minimum SIP is ₹500 [source:sbi_bluechip_key_facts]."
7. Each bullet.sources entry must use ONLY doc_id, chunk_index, doc_type, section, and score
   values as shown in the CONTEXT PASSAGES header lines below.
8. If the context cannot answer the question, say so explicitly rather than guessing.

OUTPUT: Produce exactly 6 bullets. Each bullet.sources list must reference only doc_ids
present in the context header lines provided.
"""


class _BulletsOnly(BaseModel):
    """Intermediate response model: only the 6 bullets are LLM-generated."""

    bullets: conlist(Bullet, min_length=6, max_length=6)  # type: ignore[valid-type]


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _to_citations(chunks: list[dict[str, Any]]) -> list[Citation]:
    out: list[Citation] = []
    for ch in chunks:
        meta = ch.get("metadata", {})
        raw = ch.get("rerank_score", ch.get("rrf_score", 0.0))
        out.append(
            Citation(
                doc_id=ch["doc_id"],
                chunk_index=int(meta.get("chunk_index", 0)),
                score=round(min(max(_sigmoid(float(raw)), 0.0), 1.0), 4),
                doc_type=DocType(meta.get("doc_type", "factsheet")),
                section=meta.get("section", "main"),
            )
        )
    return out


def _context_block(chunks: list[dict[str, Any]]) -> str:
    lines = ["CONTEXT PASSAGES:"]
    for ch in chunks:
        meta = ch.get("metadata", {})
        raw = ch.get("rerank_score", ch.get("rrf_score", 0.0))
        score = round(min(max(_sigmoid(float(raw)), 0.0), 1.0), 4)
        lines.append(
            f"\n--- doc_id={ch['doc_id']} | chunk_index={meta.get('chunk_index', 0)}"
            f" | doc_type={meta.get('doc_type', 'factsheet')}"
            f" | section={meta.get('section', 'main')} | score={score} ---"
        )
        lines.append(ch["text"])
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _retriever() -> HybridRetriever:
    return HybridRetriever(_CHROMA_DIR, _BM25_DIR)


@lru_cache(maxsize=1)
def _reranker() -> CrossEncoderReranker:
    return CrossEncoderReranker()


class KnowledgeAnswerer:
    def __init__(self) -> None:
        self._client = get_instructor_primary()

    def answer(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        route: str,
        request_id: str,
    ) -> dict[str, Any]:
        if route == "refuse":
            log.info("KnowledgeAnswerer: refused query='{}'", query[:60])
            return {
                "refused": True,
                "message": _REFUSAL_MSG,
                "educational_link": _EDUCATIONAL_LINK,
            }

        retrieved = _to_citations(chunks)
        retrieved_ids = {c.doc_id for c in retrieved}
        user_msg = (
            f"Query: {query}\nRoute: {route}\nRequest-ID: {request_id}\n\n"
            f"{_context_block(chunks)}\n\n"
            "Produce exactly 6 cited bullets answering the query from the context above."
        )

        log.info(
            "KnowledgeAnswerer.answer: model={} chunks={} route={}",
            _MODEL,
            len(chunks),
            route,
        )
        try:
            resp: _BulletsOnly = self._client.chat.completions.create(
                model=_MODEL,
                response_model=_BulletsOnly,
                max_retries=3,
                messages=[
                    {"role": "system", "content": _SYS_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
            )
            # Reject hallucinated doc_ids before constructing the validated RAGAnswer
            invalid = {
                src.doc_id
                for bullet in resp.bullets
                for src in bullet.sources
                if src.doc_id not in retrieved_ids
            }
            if invalid:
                log.warning("KnowledgeAnswerer: hallucinated doc_ids={}", invalid)
                return {"error": True, "message": "Unable to generate answer."}

            rag = RAGAnswer(
                query=query,
                route=QueryRoute(route),
                bullets=resp.bullets,
                retrieved_chunks=retrieved,
                model_name=_MODEL,
                request_id=request_id,
            )
            log.info("KnowledgeAnswerer.answer: OK bullets={}", len(rag.bullets))
            return rag.model_dump(mode="json")
        except Exception as exc:
            log.error("KnowledgeAnswerer.answer: failed exc={}", str(exc)[:300])
            return {"error": True, "message": "Unable to generate answer."}


def ask(query: str, request_id: str | None = None) -> dict[str, Any]:
    """Route → retrieve → rerank → answer. Module-level convenience function."""
    req_id = request_id or uuid.uuid4().hex[:8]
    route = route_query(query)
    if route == "refuse":
        return {
            "refused": True,
            "message": _REFUSAL_MSG,
            "educational_link": _EDUCATIONAL_LINK,
        }
    chunks = _retriever().retrieve(query, top_k=10)
    reranked = _reranker().rerank(query, chunks, top_k=3)
    return KnowledgeAnswerer().answer(query, reranked, route, req_id)
