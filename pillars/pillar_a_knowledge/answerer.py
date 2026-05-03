# pillars/pillar_a_knowledge/answerer.py

from __future__ import annotations

import uuid
import os
from functools import lru_cache
from pathlib import Path

from core.logger import log
from pillars.pillar_a_knowledge.retriever import HybridRetriever
from pillars.pillar_a_knowledge.router import route_query

import streamlit as st
from groq import Groq


@st.cache_resource(show_spinner="Loading knowledge base…")
def get_cached_retriever():
    return HybridRetriever(Path("data/chroma_db"), Path("data/bm25_index"))


_MODEL = "llama-3.1-8b-instant"   # 8B: ~6× faster than 70B, sufficient for factual answers
_RETRIEVE_TOP_K = 5                # 5 chunks: fast retrieval, sufficient context
_ANSWER_TOP_K = 3                  # pass top 3 to LLM

_REFUSAL_MSG = (
    "I can only provide factual information from official sources. "
    "I cannot give investment advice."
)

_SYS_PROMPT = """You are a factual mutual fund assistant.
Answer strictly from context.
Return exactly 3 short bullet points.
Each bullet must include [source:<doc_id>].
No duplication. No extra text."""


def _context_block(chunks: list[dict]) -> str:
    lines = ["CONTEXT:"]
    for ch in chunks:
        lines.append(f"\n--- doc_id={ch['doc_id']} ---")
        lines.append(ch["text"])
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _answerer():
    return KnowledgeAnswerer()


class KnowledgeAnswerer:
    def __init__(self):
        # ✅ SAFE API KEY HANDLING
        self._client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

    def answer(self, query: str, chunks: list, route: str, request_id: str):

        if route == "refuse":
            return {
                "refused": True,
                "message": _REFUSAL_MSG
            }

        formatted_chunks = "\n".join(
            f"[doc_id={ch['doc_id']}] {ch['text']}" for ch in chunks
        )

        system_prompt = f"""You are a FACTS-ONLY mutual fund assistant for SBI Mutual Fund schemes.

SAFETY: Refuse investment advice (buy/sell/recommend/predict) and PII requests with: "I cannot provide investment advice."

GROUNDING: Use ONLY the source documents below. Every fact must cite [source:doc_id]. Never use outside knowledge. If a fact is not in sources, omit it.

FORMAT: Exactly 6 bullets. Each bullet: one fact + [source:doc_id]. Answer only what was asked.

SOURCES:
{formatted_chunks}"""

        try:
            resp = self._client.chat.completions.create(
                model=_MODEL,
                temperature=0,
                max_tokens=400,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
            )

            answer_text = resp.choices[0].message.content

            if not answer_text:
                answer_text = "No answer found in knowledge base."

            bullet_lines = [
                line.strip().lstrip("•-* ")
                for line in answer_text.strip().splitlines()
                if line.strip()
            ]
            bullets = [{"text": line, "sources": []} for line in bullet_lines if line]

            # Output validation — must have at least one bullet
            if not bullets:
                return {
                    "refused": False,
                    "error": True,
                    "message": "Answer generation failed validation — no bullets produced",
                    "query": query,
                    "route": route,
                    "bullets": [],
                    "model_name": _MODEL,
                    "request_id": request_id,
                }

            # Warn if no bullets contain source citations
            has_any_source = any("[source:" in b["text"] for b in bullets)
            if not has_any_source:
                return {
                    "refused": False,
                    "error": True,
                    "message": "Answer missing source citations",
                    "query": query,
                    "route": route,
                    "bullets": [],
                    "model_name": _MODEL,
                    "request_id": request_id,
                }

            return {
                "refused": False,
                "error": False,
                "query": query,
                "route": route,
                "bullets": bullets,
                "model_name": _MODEL,
                "request_id": request_id,
            }

        except Exception as exc:
            import traceback
            print("[ERROR]", str(exc))
            traceback.print_exc()

            return {
                "refused": False,
                "error": True,
                "message": str(exc),
                "request_id": request_id
            }


def ask(query: str, request_id: str | None = None):
    # HARD SAFETY CHECK — first line of defense before any LLM call
    from pillars.pillar_a_knowledge.safety import check_safety
    safety_result = check_safety(query)
    if not safety_result["safe"]:
        return {
            "refused": True,
            "error": False,
            "message": safety_result["message"],
            "query": query,
            "route": "refuse",
            "bullets": [],
            "model_name": "safety_layer",
            "request_id": request_id or uuid.uuid4().hex[:8],
        }

    req_id = request_id or uuid.uuid4().hex[:8]

    try:
        import time
        t0 = time.perf_counter()

        route = route_query(query, _safety_checked=True)   # safety already ran above
        t1 = time.perf_counter()
        log.info("ask: route={} ({:.2f}s) query='{}'", route, t1 - t0, query[:60])

        if route == "refuse":
            return {"refused": True, "message": _REFUSAL_MSG}

        chunks = get_cached_retriever().retrieve(query, top_k=_RETRIEVE_TOP_K)
        t2 = time.perf_counter()
        log.info("ask: retrieval {:.2f}s ({} chunks)", t2 - t1, len(chunks))

        top_chunks = chunks[:_ANSWER_TOP_K]   # skip reranker — top-3 from hybrid RRF is sufficient

        result = _answerer().answer(query, top_chunks, route, req_id)
        t3 = time.perf_counter()
        log.info("ask: llm {:.2f}s  total {:.2f}s", t3 - t2, t3 - t0)
        return result

    except Exception as exc:
        import traceback
        print(f"[ERROR] ask() failed: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return {
            "refused": False,
            "error": True,
            "message": f"System error: {exc}",
            "route": "N/A",
            "model_name": "N/A",
            "bullets": [],
            "request_id": req_id,
        }


def prewarm_knowledge_base():
    get_cached_retriever()
    _answerer()