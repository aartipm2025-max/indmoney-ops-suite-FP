"""
tests/test_p3_pillar_a.py

Phase 3 — Pillar A: chunker, retriever, reranker, router unit tests.
Does NOT test answerer (requires live Groq API).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pillars.pillar_a_knowledge.chunker import chunk_all_sources, chunk_markdown_file
from pillars.pillar_a_knowledge.reranker import CrossEncoderReranker
from pillars.pillar_a_knowledge.retriever import HybridRetriever
from pillars.pillar_a_knowledge.router import route_query

_ROOT = Path(__file__).parent.parent
_FACTSHEETS = _ROOT / "data" / "factsheets" / "markdown"
_FEES = _ROOT / "data" / "fees"
_CHROMA = _ROOT / "data" / "chroma_db"
_BM25 = _ROOT / "data" / "bm25_index"
_BLUECHIP = _FACTSHEETS / "sbi_bluechip.md"

_EXPECTED_SECTIONS = {
    "fund_overview",
    "key_facts",
    "expense_ratio",
    "exit_load",
    "minimum_investment",
    "top_holdings",
    "taxation",
}


# ---------------------------------------------------------------------------
# Chunker tests
# ---------------------------------------------------------------------------

def test_chunker_produces_correct_count():
    chunks = chunk_all_sources(_FACTSHEETS, _FEES)
    assert len(chunks) == 41, f"Expected 41 chunks, got {len(chunks)}"


def test_chunker_metadata_fields():
    chunks = chunk_markdown_file(_BLUECHIP)
    assert chunks, "No chunks returned for sbi_bluechip.md"
    for chunk in chunks:
        assert "text" in chunk
        assert "metadata" in chunk
        assert "doc_id" in chunk
        meta = chunk["metadata"]
        for field in ("fund_name", "doc_type", "section", "source_url", "chunk_index", "file_name"):
            assert field in meta, f"Missing metadata field: {field}"


def test_chunker_sections_match_headings():
    chunks = chunk_markdown_file(_BLUECHIP)
    for chunk in chunks:
        section = chunk["metadata"]["section"]
        assert section in _EXPECTED_SECTIONS, (
            f"Unexpected section '{section}' — not in {_EXPECTED_SECTIONS}"
        )


# ---------------------------------------------------------------------------
# Retriever tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def retriever() -> HybridRetriever:
    return HybridRetriever(_CHROMA, _BM25)


def test_retriever_returns_10(retriever: HybridRetriever):
    results = retriever.retrieve("exit load SBI Bluechip", top_k=10)
    assert len(results) == 10, f"Expected 10 results, got {len(results)}"
    for r in results:
        for key in ("doc_id", "text", "metadata", "rrf_score"):
            assert key in r, f"Result missing key: {key}"


def test_retriever_relevant_top3(retriever: HybridRetriever):
    results = retriever.retrieve("expense ratio SBI Small Cap", top_k=10)
    top3_ids = [r["doc_id"] for r in results[:3]]
    assert "sbi_small_cap_expense_ratio" in top3_ids, (
        f"Expected 'sbi_small_cap_expense_ratio' in top-3, got {top3_ids}"
    )


# ---------------------------------------------------------------------------
# Reranker tests
# ---------------------------------------------------------------------------

def test_reranker_reduces(retriever: HybridRetriever):
    candidates = retriever.retrieve("exit load SBI Bluechip", top_k=10)
    reranker = CrossEncoderReranker()
    top3 = reranker.rerank("exit load SBI Bluechip", candidates, top_k=3)
    assert len(top3) == 3, f"Expected 3 results after reranking, got {len(top3)}"
    for r in top3:
        assert "rerank_score" in r, "Result missing 'rerank_score'"


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

def test_router_fact():
    assert route_query("What is the NAV of SBI Midcap Fund?") == "fact_only"


def test_router_fee():
    assert route_query("What is exit load?") == "fee_only"


def test_router_both():
    assert route_query("What is the exit load for ELSS fund and why?") == "both"


def test_router_refuses_advice():
    assert route_query("Should I invest in SBI Small Cap?") == "refuse"
