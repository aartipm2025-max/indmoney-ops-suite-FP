# pillars/pillar_a_knowledge/answerer.py

from __future__ import annotations

import uuid
import os
from functools import lru_cache
from pathlib import Path

from core.logger import log
from pillars.pillar_a_knowledge.reranker import CrossEncoderReranker
from pillars.pillar_a_knowledge.retriever import HybridRetriever
from pillars.pillar_a_knowledge.router import route_query

import streamlit as st
from groq import Groq


@st.cache_resource(show_spinner="Loading knowledge base (first time only)...")
def get_cached_retriever():
    return HybridRetriever(Path("data/chroma_db"), Path("data/bm25_index"))


@st.cache_resource(show_spinner="Loading reranker (first time only)...")
def get_cached_reranker():
    return CrossEncoderReranker()


# 🔽 FAST MODEL (IMPORTANT)
_MODEL = "llama-3.1-8b-instant"

_RERANK_CANDIDATES = 5
_RERANK_TOP_K = 3

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

        system_prompt = f"""You are a facts-only mutual fund assistant for SBI Mutual Fund schemes.
You answer questions using ONLY the provided source documents.

CRITICAL RULES:
1. Answer in EXACTLY 6 bullet points.
2. Answer ONLY what the user asked. Do NOT include information about other funds unless explicitly asked for comparison.
3. If the user asks about "SBI Bluechip Fund", answer ONLY about SBI Bluechip Fund. Do NOT mention SBI Midcap, SBI Small Cap, or other funds.
4. Each bullet must have [source:doc_id] at the END of the sentence, not inline.
5. Only cite doc_ids that appear in the provided chunks.
6. Stay strictly within the provided text.
7. Never give investment advice, recommendations, or predictions.
8. Never disclose PII.
9. Keep each bullet to 1-2 sentences maximum.
10. If you only have 3-4 relevant facts, repeat or rephrase key information to reach exactly 6 bullets. DO NOT add information from other funds to fill space.

Available source documents:
{formatted_chunks}

User question: {query}

Format each bullet as:
- The fact in plain text [source:doc_id]

All sources will be displayed separately at the end, so DO NOT group them after each bullet.
"""

        print("[DEBUG] Calling LLM")

        try:
            resp = self._client.chat.completions.create(
                model=_MODEL,
                temperature=0,
                max_tokens=600,
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
    req_id = request_id or uuid.uuid4().hex[:8]

    try:
        print(f"[DEBUG] Step 1: Routing query: {query[:80]}")
        route = route_query(query)
        print(f"[DEBUG] Route result: {route!r}")

        if route == "refuse":
            print("[DEBUG] Query refused")
            return {"refused": True, "message": _REFUSAL_MSG}

        print("[DEBUG] Step 2: Retrieving chunks")
        chunks = get_cached_retriever().retrieve(query, top_k=_RERANK_CANDIDATES)
        print(f"[DEBUG] Retrieved {len(chunks)} chunks")

        reranked = chunks[:_RERANK_TOP_K]

        print("[DEBUG] Step 4: Generating answer")
        result = _answerer().answer(query, reranked, route, req_id)
        print(f"[DEBUG] Answer generated: {type(result)}")
        print(f"[DEBUG] Answer dict keys: {list(result.keys())}")
        print(f"[DEBUG] Has 'route': {'route' in result}")
        print(f"[DEBUG] Has 'bullets': {'bullets' in result}")
        print(f"[DEBUG] Has 'model_name': {'model_name' in result}")
        if "error" in result:
            print(f"[DEBUG] Error flag: {result.get('error')}")
            print(f"[DEBUG] Error message: {result.get('message', 'N/A')}")

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


# ✅ REQUIRED FOR app.py
def prewarm_knowledge_base():
    get_cached_retriever()
    get_cached_reranker()
    _answerer()