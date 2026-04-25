# Pillar A — Smart-Sync Knowledge Base: RAG Design

## Purpose

Pillar A merges M1 (Mutual Fund FAQ) with M2 (Fee Explainer) into a unified search surface. A user asks one question; the system retrieves from both factsheets AND fee docs and answers in exactly 6 cited bullets. There is no separate FAQ bot and no separate fee bot — one query interface, one ranked result list, one structured answer.

The 6-bullet contract is enforced by a Pydantic schema (`RAGAnswer`) validated at inference time via Instructor. Every bullet must carry an inline `[source:doc_id]` citation that cross-references the retrieved chunks. Answers with fewer or more bullets, or with citations to doc IDs not present in the retrieved set, are rejected and retried automatically.

---

## Data Sources

| Asset | Location | Count |
|---|---|---|
| SBI MF factsheet markdown | `data/factsheets/markdown/` | 5 files |
| ELSS exit load fee doc | `data/fees/elss_exit_load.md` | 1 file |
| **Total** | | **6 documents** |

All 6 documents are manually curated from official public sources (`sbimf.com`, `sebi.gov.in`, `investor.sebi.gov.in`). No synthetic content. Source URLs and retrieval dates are in each file's YAML frontmatter and in `data/manifests/source_manifest.json`.

---

## Chunking Strategy

Splitting is markdown-header-aware: chunks are cut at H2 (`##`) boundaries so no single chunk ever spans two logical sections. This keeps retrieved passages self-contained and citation-accurate.

**Metadata inherited by every chunk**

| Field | Values | Notes |
|---|---|---|
| `fund_name` | e.g. `"SBI Bluechip Fund"` | Extracted from frontmatter or H1 |
| `doc_type` | `factsheet` \| `fee` | Determines retrieval routing |
| `section` | e.g. `"exit_load"`, `"expense_ratio"`, `"key_facts"` | Derived from H2 heading text |
| `source_url` | Frontmatter `source_url` value | For citation traceability |
| `chunk_index` | Integer, 0-based within document | For ordering within a doc |

**Sizing**

- Target: ~500 tokens per chunk
- Overlap: ~75 tokens between consecutive chunks within the same section to preserve cross-sentence context

**Document-level summary prefix**

Every chunk is prepended with a one-line document summary before embedding, e.g.:

```
[SBI Bluechip Fund | factsheet | expense_ratio] SBI Large Cap Fund — SEBI categorised large cap equity scheme, AUM ₹33,699 crore, TER regular 1.57%, TER direct 0.64%.
```

This prefix improves retrieval accuracy on specific numeric queries by providing context that would otherwise require the model to read the full document. Technique validated in Snowflake 2025 embedding research.

---

## Embedding Model

**Model:** `BAAI/bge-small-en-v1.5`

| Property | Value |
|---|---|
| Dimensions | 384 |
| License | MIT |
| Inference | Local CPU (no API cost, no data egress) |
| Avg MTEB retrieval score | +3–5% over `all-MiniLM-L6-v2` at identical parameter count |

The model is loaded once at startup via `sentence-transformers` and kept in memory. For a 6-document corpus, the full index fits in ~4 MB of memory. No GPU required.

---

## Vector Store

**Backend:** ChromaDB persistent (local, Rust-backed rewrite shipped in 2025)

| Property | Value |
|---|---|
| Collection name | `sbi_mf_knowledge` |
| Persistence path | `data/vectorstore/chroma/` |
| Distance metric | Cosine |
| Metadata fields | `fund_name`, `doc_type`, `section`, `source_url`, `chunk_index` |

ChromaDB is chosen over FAISS because it stores metadata natively alongside vectors, which makes filtered retrieval (e.g., `doc_type == "factsheet"`) a single call without a separate metadata store.

---

## Hybrid Retrieval

Pure dense retrieval misses exact-match queries like "exit load 1%", "₹500 minimum SIP", or "BSE 100 TRI". Pure BM25 misses semantic paraphrases. The pipeline runs both in parallel and fuses the results.

**BM25 — sparse**

- Library: `bm25s` (pure Python, no Elasticsearch dependency)
- Index built at ingestion time from the same chunked corpus
- Catches exact financial terms, fund names, numeric values

**Dense — semantic**

- ChromaDB similarity search over `BAAI/bge-small-en-v1.5` embeddings
- Catches paraphrased queries, concept-level matches

**Fusion — Reciprocal Rank Fusion (RRF)**

```
RRF_score(d) = 0.3 × (1 / (k + rank_bm25(d)))
             + 0.7 × (1 / (k + rank_dense(d)))
  where k = 60
```

The 0.3/0.7 split reflects that English financial prose benefits more from semantic matching than keyword overlap. `k=60` is the standard RRF constant that dampens rank differences at the top of the list.

Both retrievers return top-10 candidates; after RRF the merged list is re-ranked to a final top-10 before passing to the cross-encoder.

---

## Reranking

**Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`

| Property | Value |
|---|---|
| Inference | Local CPU |
| License | Apache 2.0 |
| Input | Query + chunk text pairs |
| Latency | ~100 ms per query on CPU |
| Input size | Top-10 from RRF |
| Output size | Top-3 passed to answer generation |

Cross-encoders outperform bi-encoder similarity for reranking because they attend jointly over query and passage. The 100 ms CPU cost is acceptable for interactive use (total pipeline target: < 2 s).

---

## Query Router

The router classifies each incoming query into one of three retrieval targets before retrieval begins, so the dense search space is narrowed and precision improves.

**Stage 1 — Regex pre-filter** (zero latency)

| Pattern | Route |
|---|---|
| Fund name found in query (SBI Bluechip, SBI Small Cap, …) | `fact_only` |
| Keywords: exit load, expense ratio, TER, fee, charge, lock-in | `fee_only` |
| No match | Falls through to Stage 2 |

**Stage 2 — LLM classification** (Groq API, ~200 ms)

- Model: `llama-3.1-8b-instant` via Groq
- Framework: Instructor with `mode=TOOL_CALL`
- Output type: `Literal["fact_only", "fee_only", "both"]`
- Called only when regex stage produces no match

**Routing behaviour**

| Route | Retrieval scope |
|---|---|
| `fact_only` | ChromaDB filter `doc_type == "factsheet"` |
| `fee_only` | ChromaDB filter `doc_type == "fee"` |
| `both` | No filter — full 6-document corpus |

---

## Answer Generation

**Model:** `llama-3.3-70b-versatile` via Groq API

| Property | Value |
|---|---|
| Framework | Instructor, `mode=TOOLS` |
| Response schema | `RAGAnswer` (from `schemas/rag.py`) |
| Bullet count | Exactly 6 (`conlist(Bullet, min_length=6, max_length=6)`) |
| Citation requirement | Each `Bullet.sources` list must contain ≥ 1 `[source:doc_id]` tag |
| Citation validation | Post-generation regex check + cross-reference against retrieved chunk IDs |
| Auto-retry | Up to 3 attempts on `ValidationError` (Instructor `max_retries=3`) |

The system prompt passes the top-3 reranked chunks as context, the query route, and the 8 safety rules. The LLM is instructed to draw only from the provided context and cite every claim.

---

## Safety

The system prompt enforces these 8 rules on every call:

1. Answer only from the provided context passages. Do not use training knowledge.
2. Never recommend buying, selling, or holding any fund.
3. Never state or imply projected returns or guaranteed performance.
4. Never request or repeat PAN, Aadhaar, bank account, or contact details.
5. If asked for investment advice, respond: *"I can share factual information about this fund, but I'm not able to give investment advice. For personalised guidance, speak to a SEBI-registered advisor."*
6. Every factual claim must include `[source:doc_id]`.
7. If the answer cannot be supported by the retrieved context, say so explicitly rather than guessing.
8. Do not speculate about fund performance, future NAV, or market conditions.

Refusal responses do not count toward the 6-bullet contract — they are returned as a plain string outside the `RAGAnswer` schema.

---

## Retrieval Pipeline Flow

```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│  Stage 1: Regex Pre-filter          │
│  fund name → fact_only              │
│  fee keyword → fee_only             │
│  no match   → Stage 2               │
└─────────────────────────────────────┘
    │                   │
    │ matched           │ no match
    │                   ▼
    │       ┌──────────────────────────┐
    │       │  Stage 2: LLM Router     │
    │       │  Groq llama-3.1-8b       │
    │       │  → fact_only|fee_only|both│
    │       └──────────────────────────┘
    │                   │
    └──────────┬─────────┘
               │ route: fact_only | fee_only | both
               ▼
    ┌──────────────────────────────────────────┐
    │  Parallel Retrieval                       │
    │                                           │
    │  BM25 (bm25s)        ChromaDB dense       │
    │  top-10 candidates   top-10 candidates    │
    │  sparse keyword      semantic embedding   │
    └──────────────────────────────────────────┘
               │
               ▼
    ┌──────────────────────────────┐
    │  Reciprocal Rank Fusion      │
    │  k=60, 0.3 BM25 + 0.7 dense │
    │  → merged top-10             │
    └──────────────────────────────┘
               │
               ▼
    ┌──────────────────────────────────────────┐
    │  Cross-Encoder Reranker                   │
    │  cross-encoder/ms-marco-MiniLM-L-6-v2    │
    │  top-10 in → top-3 out (~100 ms CPU)      │
    └──────────────────────────────────────────┘
               │
               ▼
    ┌──────────────────────────────────────────┐
    │  Answer Generation                        │
    │  Groq llama-3.3-70b-versatile            │
    │  Instructor mode=TOOLS                    │
    │  RAGAnswer: exactly 6 cited bullets       │
    │  Auto-retry up to 3× on ValidationError   │
    └──────────────────────────────────────────┘
               │
               ▼
    ┌──────────────────────────────┐
    │  Citation Validator          │
    │  regex [source:doc_id]       │
    │  cross-ref retrieved IDs     │
    │  fail → retry (counted above)│
    └──────────────────────────────┘
               │
               ▼
         RAGAnswer
    (6 bullets, all cited)
```
