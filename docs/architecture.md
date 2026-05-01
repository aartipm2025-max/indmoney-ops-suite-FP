# System Architecture

## Overview

The INDmoney Investor Ops & Intelligence Suite is organised as three independent functional pillars sharing a common core layer. Each pillar owns its own data, logic, and UI tab. The core layer provides LLM access, logging, exception handling, and schema contracts used across all pillars.

```
User (Browser)
     │
     ▼
Streamlit App (app.py)
     │
     ├── Tab A: Ask Funds ──────────► Pillar A (Knowledge Base / RAG)
     ├── Tab B: Weekly Pulse ───────► Pillar B (Review Intelligence)
     ├── Tab C: Voice Scheduler ────► Pillar B (Voice Agent)
     ├── Tab D: Action Approval ────► Pillar C (HITL Ops)
     └── Tab E: Evals ─────────────► evals/ (eval framework)
```

---

## Pillar A — Knowledge Base (RAG)

### Data Flow

```
User query (natural language)
        │
        ▼
┌─────────────────────────────────┐
│         Safety Layer            │
│  safety.py :: check_safety()    │
│                                 │
│  1. Regex: investment advice?   │  ──► {"safe": False} → refuse immediately
│  2. Regex: PII request?         │      (zero LLM cost)
└──────────────┬──────────────────┘
               │ safe
               ▼
┌─────────────────────────────────┐
│         Query Router            │
│  router.py :: route_query()     │
│                                 │
│  1. Safety re-check (backup)    │
│  2. Regex: fee_only / fact_only │  ──► "refuse" / "fact_only" / "fee_only" / "both"
│  3. LLM fallback (Groq fast)    │
└──────────────┬──────────────────┘
               │ route
               ▼
┌─────────────────────────────────┐
│       Hybrid Retriever          │
│  retriever.py :: retrieve()     │
│                                 │
│  ┌──────────┐  ┌─────────────┐  │
│  │  BM25    │  │  ChromaDB   │  │
│  │ (sparse) │  │  (dense)    │  │
│  │ bm25s    │  │ BAAI/bge-sm │  │
│  └────┬─────┘  └──────┬──────┘  │
│       │  RRF fusion   │         │
│       └───────┬───────┘         │
│           top-k chunks          │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│       Cross-Encoder Reranker    │
│  reranker.py :: rerank()        │
│  ms-marco-MiniLM-L-6-v2        │
│  max_len=256, top_k=3           │
└──────────────┬──────────────────┘
               │ reranked chunks
               ▼
┌─────────────────────────────────┐
│         LLM Answerer            │
│  answerer.py :: answer()        │
│  Groq llama-3.1-8b-instant     │
│  temperature=0, max_tokens=600  │
│                                 │
│  Output: 6 grounded bullets     │
│  Each: fact + [source:doc_id]   │
│                                 │
│  Validation: has bullets?       │
│             has [source:] tags? │
└──────────────┬──────────────────┘
               │
               ▼
         dict response:
         {refused, bullets,
          route, model_name,
          request_id}
```

### Indexing Pipeline

```
data/factsheets/markdown/ + data/fees/
           │
           ▼
    chunker.py (MarkdownChunker)
    Split on ## headers, parse YAML frontmatter
    Adds: doc_id, source_file, chunk_index
           │
           ├──► ChromaDB (PersistentClient)
           │    Collection: "sbi_mf_knowledge"
           │    Embedding: BAAI/bge-small-en-v1.5
           │
           └──► BM25 index (bm25s)
                Saved: data/bm25_index/
                Files: corpus.mmindex.json,
                       params.index.json,
                       vocab.index.json
```

### Retrieval Fusion (RRF)

Reciprocal Rank Fusion combines BM25 rank and ChromaDB rank:

```
score(d) = 1 / (60 + r_bm25(d))  +  1 / (60 + r_dense(d))
```

Top-10 fused results are re-ranked by the cross-encoder to yield the final top-3.

---

## Pillar B — Review Intelligence & Voice Agent

### Review → Pulse Pipeline

```
Google Play Store (id=in.indwealth)
           │
           ▼ scripts/scrape_reviews.py
data/reviews/raw/indmoney_playstore_raw.json
           │
           ▼ scripts/clean_reviews.py
Cleaned DataFrame (reviews.csv)
           │
     ┌─────┴──────┐
     ▼            ▼
themes.py     trends.py
(LLM)         (pandas+scipy)
     │            │
     │  batch 100 reviews
     │  Map: fast LLM → ≤5 themes/batch
     │  Reduce: merge similar, sum counts
     │            │
     └─────┬──────┘
           │ themes + week-over-week deltas
           ▼
        pulse.py
        LLM (primary: llama-3.3-70b-versatile)
        Pydantic-validated:
          - summary ≤250 words
          - actions = exactly 3
           │
           ▼
        Pulse dict → stored in st.session_state
```

### Voice Agent State Machine

```
GREETING
    │ any input
    ▼
DISCLAIMER  ←────────────────────────┐
    │ "yes" / "I agree"              │
    ▼                                │
TOPIC_SELECT                         │
    │ user picks 1–5                 │
    ▼                                │
TIME_PREFERENCE                      │
    │ "morning" / "afternoon" / etc. │
    ▼                                │
SLOT_OFFER                           │
    │ user confirms / picks slot     │
    ▼                                │
CONFIRMATION                         │
    │ "yes" confirms                 │ "no" re-starts
    ▼                                │
BOOKED ──────────────────────────────┘
    (generates booking code IND-{THEME}-{DATE}-{SEQ})
    (pushes 3 ops to HITL queue: Calendar + Email + Doc)
```

Booking code example: `IND-TECH-20260501-001`

Topic options: KYC/Onboarding · SIP/Mandates · Statements/Tax · Withdrawals · Account Changes

---

## Pillar C — HITL Operations

### Approval Flow

```
Booking completed (Voice Agent)
           │
           ▼
mcp_tools.py
  create_calendar_hold()   ──┐
  create_email_draft()    ──┤──► 3 PendingOp records inserted
  create_doc_append()     ──┘    into data/hitl_queue.db (WAL mode)

           │  (Tab D renders pending ops on load)
           ▼
Human reviews in Streamlit UI
           │
    ┌──────┴────────┐
    ▼               ▼
  Approve         Reject
    │               │
    ▼               │
Google API calls:   │
  Calendar.insert() │
  Gmail.create()    │
  Docs.batchUpdate()│
    │               │
    ▼               ▼
status="executed"  status="rejected"
                   reason + detail stored
```

### HITL Queue Schema

```sql
CREATE TABLE pending_ops (
    id               TEXT PRIMARY KEY,
    op_type          TEXT NOT NULL,       -- calendar_hold|email_draft|doc_append
    status           TEXT NOT NULL DEFAULT 'pending',
    payload_json     TEXT NOT NULL,
    idempotency_key  TEXT UNIQUE,         -- booking_code scoped
    created_at       TEXT NOT NULL,
    approved_at      TEXT,
    executed_at      TEXT,
    retry_count      INTEGER DEFAULT 0,
    last_error       TEXT
);
```

State transitions: `pending → approved → executed` or `pending → rejected`.

---

## Core Layer

### LLM Client & Circuit Breaker

```
LLMClient.chat()
    │
    ├── _check_circuit()
    │       if open → raise LLMCircuitBreakerError (no API call)
    │
    ├── Groq API call  timeout=30s
    │       on APIError / RateLimitError → tenacity retry
    │       max_attempts=3, wait=exponential(2s..10s)
    │
    ├── on success → _reset_failures()
    │
    └── on failure → _record_failure()
            count >= 5 within 60s window?
            → circuit opens for 30s
```

### Request Tracing

The request ID propagates via Python `contextvars` through the entire call stack:

```
ask(query, request_id="a3f9c1b2")
  → route_query()   [INFO] router: fact_only        [req=a3f9c1b2]
  → retrieve()      [INFO] 10 chunks retrieved      [req=a3f9c1b2]
  → answer()        [INFO] llm call llama-3.1-8b    [req=a3f9c1b2]
```

### Logging Architecture

| Sink | Format | Rotation | Retention |
|------|--------|----------|-----------|
| `logs/app.log` | Human-readable (Loguru) | 5 MB | 5 backups |
| `logs/app.jsonl` | JSON-line (structured) | 5 MB | 5 backups |
| `logs/system_errors.log` | Errors only | 5 MB | 5 backups |
| Console | Coloured Loguru | — | — |

### Exception Hierarchy

```
OpsSuiteError
├── ConfigError
├── LLMError
│   ├── LLMRefusalError
│   ├── LLMCircuitBreakerError
│   └── LLMTimeoutError
├── RetrievalError
├── CitationError
├── SchemaValidationError
├── PulseGenerationError
├── TrendDetectionError
├── VoiceAgentError
├── BookingError
├── HITLApprovalError
├── GoogleAPIError
├── OAuthError
├── EvalError
│   └── JudgeCalibrationError
└── SafetyViolationError
    └── PIIDetectedError
```

---

## Evaluation Framework

```
scripts/run_all_evals.py
    │
    │  ThreadPoolExecutor(max_workers=3)   ← RAG + Safety + UX concurrent
    │
    ├── run_rag_eval.py
    │       ThreadPoolExecutor(max_workers=5)
    │       35 questions in parallel batches of 5
    │         ask() → judge_faithfulness() + judge_relevance()
    │         pass if both scores ≥ 0.50
    │       → evals/rag_eval_results.json
    │
    ├── run_safety_eval.py
    │       ThreadPoolExecutor(max_workers=16)
    │       16 adversarial prompts — all parallel
    │         safety layer short-circuits — zero LLM cost per prompt
    │       → evals/safety_eval_results.json
    │
    ├── run_ux_eval.py
    │       pulse_word_count ≤ 250
    │       pulse_action_count = 3
    │       voice_theme_mentioned = True
    │       → evals/ux_eval_results.json
    │
    └── generate_report.py
            → evals/EVALS.md
```

---

## Security Design

### Input Safety — Defence in Depth

| Layer | Mechanism | API cost |
|-------|-----------|----------|
| 1st | `safety.py` — deterministic regex (investment advice + PII) | Zero |
| 2nd | `router.py` — additional `refuse_patterns` backup | Zero |
| 3rd | LLM router fallback (edge cases not caught by regex) | 1 fast call |
| 4th | LLM answerer system prompt — safety rules embedded | Already-paying call |

Inputs caught at layer 1 never touch the retriever or LLM.

### Secrets Management

```
.secrets/                      ← not in git
    google_credentials.json    ← OAuth2 client secret
    google_token.json          ← refresh token (auto-managed)

.env                           ← not in git
    GROQ_API_KEY               ← required
    GEMINI_API_KEY             ← optional fallback
```

`config.py` raises `ConfigError` at startup if `GROQ_API_KEY` is absent or still the template placeholder.

---

## Performance Optimisations

| Optimisation | Location | Effect |
|-------------|----------|--------|
| `@st.cache_resource` on HybridRetriever | `answerer.py` | Model loads once per process |
| `@st.cache_resource` on CrossEncoderReranker | `answerer.py` | Avoids repeated init |
| `@lru_cache(maxsize=1)` on KnowledgeAnswerer | `answerer.py` | Singleton Groq client |
| `ThreadPoolExecutor(max_workers=5)` | `run_rag_eval.py` | ~30 s vs ~210 s sequential |
| `ThreadPoolExecutor(max_workers=16)` | `run_safety_eval.py` | All 16 prompts fully parallel |
| 3-eval concurrent run | `run_all_evals.py` | RAG + Safety + UX overlap |
| BM25 index persisted to disk | `data/bm25_index/` | No re-tokenisation on startup |
| ChromaDB persistent client | `data/chroma_db/` | Embeddings survive restarts |
| Regex safety before LLM | `safety.py` | Adversarial inputs cost zero tokens |
| `temperature=0` everywhere | `answerer.py`, `llm_judge.py` | Deterministic, reproducible eval scores |

---

## Component Map

| File / Directory | Responsibility | Phase |
|---|---|---|
| `config.py` | Typed settings, env loading, path constants | 0 |
| `core/exceptions.py` | 15-class domain exception hierarchy | 0 |
| `core/request_context.py` | ContextVar request-ID tracing | 0 |
| `core/logger.py` | Loguru console + file + JSONL sinks | 0 |
| `core/error_logger.py` | Structured error log writer | 0 |
| `core/llm_client.py` | Groq wrapper with retry + circuit breaker | 0 |
| `core/instructor_clients.py` | Instructor-patched structured-output clients | 0 |
| `schemas/` | Pydantic v2 contracts for all pillars (78 tests) | 1 |
| `pillars/pillar_a_knowledge/` | Safety + router + hybrid retrieval + reranker + answerer | 2–4 |
| `pillars/pillar_b_voice/` | Review ingestion + theme extraction + trend detection + pulse + voice FSM | 4–6 |
| `pillars/pillar_c_hitl/` | HITL queue + Google APIs + MCP tools + briefing cards | 5–7 |
| `evals/` | Eval harness, golden + adversarial datasets, LLM judge | 8–9 |
| `ui/` | Streamlit tabs for all five pillars | 3, 6, 7, 9 |
| `data/` | Factsheets, fees, ChromaDB, BM25 index, SQLite DBs | 2+ |
| `logs/` | app.log, app.jsonl, system_errors.log | 0 |
| `docs/` | ARCHITECTURE.md, SOURCES.md, design docs | 0.5, 10 |
