"""
pillars/pillar_a_knowledge/answerer.py

Phase 3 — LLM answer generation: Instructor + RAGAnswer schema.
"""

from __future__ import annotations

import math
import uuid
from copy import deepcopy
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

import streamlit as st


@st.cache_resource
def get_cached_retriever():
    from pillars.pillar_a_knowledge.retriever import HybridRetriever
    from pathlib import Path
    return HybridRetriever(Path("data/chroma_db"), Path("data/bm25_index"))


@st.cache_resource
def get_cached_reranker():
    from pillars.pillar_a_knowledge.reranker import CrossEncoderReranker
    return CrossEncoderReranker()


_MODEL = "llama-3.3-70b-versatile"
_RERANK_CANDIDATES = 6
_RERANK_TOP_K = 3
_REFUSAL_MSG = (
    "I can only provide factual information from official sources. "
    "I cannot give investment advice, recommendations, or personal data."
)
_EDUCATIONAL_LINK = "https://www.amfiindia.com/investor/knowledge-center-info"

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_CHROMA_DIR = _PROJECT_ROOT / "data" / "chroma_db"
_BM25_DIR = _PROJECT_ROOT / "data" / "bm25_index"

_SYS_PROMPT = """\
You are a crisp, factual mutual fund chatbot for SBI Mutual Fund products.

STRICT RULES — no exceptions:
1. Answer ONLY from the CONTEXT PASSAGES provided. Never use training knowledge.
2. Never recommend buying, selling, or holding any fund.
3. Never speculate about future NAV, returns, or market conditions.
4. Never request or repeat PAN, Aadhaar, bank account, or contact details.
5. If the context cannot answer the question, say so explicitly.

OUTPUT FORMAT — mandatory:
- Produce EXACTLY 3 bullets. No more, no fewer.
- Bullet 1 = direct answer to the user's question.
- Bullets 2-3 = highest-value supporting facts only (AUM, NAV, risk, top holding, expense ratio).
- Each bullet: one sentence, max 20 words, factual, no filler.
- NO duplicate facts. If two facts convey the same meaning, keep only one.
- Remove generic/obvious statements (e.g. "the fund has a fund manager").
- Each bullet text MUST contain exactly one inline citation: [source:<doc_id>].
- Each bullet.sources list must reference only doc_ids from the context headers.
- Do NOT repeat the entity name in every bullet.
"""


class _BulletsOnly(BaseModel):
    """Intermediate response model: only the 3 bullets are LLM-generated."""

    bullets: conlist(Bullet, min_length=3, max_length=3)  # type: ignore[valid-type]


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


@lru_cache(maxsize=1)
def _answerer() -> "KnowledgeAnswerer":
    return KnowledgeAnswerer()


def prewarm_knowledge_base() -> None:
    """Load and cache retrieval/rerank components at service startup."""
    log.info("Knowledge base prewarm: starting")
    _retriever()
    _reranker()
    _answerer()
    log.info("Knowledge base prewarm: completed")


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
            f"Query: {query}\nRoute: {route}\n\n"
            f"{_context_block(chunks)}\n\n"
            "Produce exactly 3 cited bullets answering the query from the context above. "
            "Bullet 1 = direct answer. Bullets 2-3 = top supporting facts. No duplication."
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
                temperature=0,
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
    """Route → retrieve → rerank → answer with per-query cache for steady state."""
    req_id = request_id or uuid.uuid4().hex[:8]
    result = deepcopy(_cached_ask(query))
    if not result.get("refused") and not result.get("error"):
        result["request_id"] = req_id
    return result


@lru_cache(maxsize=128)
def _cached_ask(query: str) -> dict[str, Any]:
    """Cache full answers for repeated queries to avoid repeated LLM/rerank calls."""
    req_id = "cached"
    route = route_query(query)
    if route == "refuse":
        return {
            "refused": True,
            "message": _REFUSAL_MSG,
            "educational_link": _EDUCATIONAL_LINK,
        }
    chunks = get_cached_retriever().retrieve(query, top_k=_RERANK_CANDIDATES)
    reranked = get_cached_reranker().rerank(query, chunks, top_k=_RERANK_TOP_K)
    return _answerer().answer(query, reranked, route, req_id)
