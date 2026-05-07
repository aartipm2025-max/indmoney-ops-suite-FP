# INDmoney Investor Ops & Intelligence Suite

> A production-grade, three-pillar AI operations platform — built as a capstone portfolio project demonstrating end-to-end ML system design, retrieval-augmented generation, voice intelligence, and human-in-the-loop workflows.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     STREAMLIT DASHBOARD  (5 Tabs)                    │
│  ┌──────────┐  ┌─────────────┐  ┌────────────┐  ┌────────────────┐  │
│  │Ask Funds │  │Weekly Pulse │  │Voice Sched.│  │Action Approval │  │
│  └────┬─────┘  └──────┬──────┘  └─────┬──────┘  └───────┬────────┘  │
└───────│───────────────│───────────────│──────────────────│────────────┘
        │               │               │                  │
        ▼               ▼               ▼                  ▼
┌──────────────┐  ┌─────────────────────────┐  ┌────────────────────┐
│  PILLAR A    │  │       PILLAR B           │  │     PILLAR C       │
│  Knowledge   │  │  Review Intelligence     │  │   HITL Operations  │
│  Base (RAG)  │  │  + Voice Agent           │  │                    │
│              │  │                          │  │  Approval Queue    │
│ Safety Layer │  │  Play Store reviews      │  │  (SQLite WAL)      │
│ Query Router │  │  Theme extraction (LLM)  │  │                    │
│ Hybrid Retr. │  │  Trend detection (scipy) │  │  Google Calendar   │
│  BM25+Chroma │  │  Pulse (≤250w, 3 acts)  │  │  Gmail Drafts      │
│ CrossEncoder │  │  Voice FSM (7 states)    │  │  Google Docs       │
│ LLM Answerer │  │  Booking code gen        │  │  MCP tool defs     │
└──────┬───────┘  └────────────┬────────────┘  └────────┬───────────┘
       └─────────────────────────────────────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │           CORE LAYER            │
              │  LLMClient · Circuit Breaker    │
              │  Retry × 3 · 30s timeout        │
              │  Loguru structured logs         │
              │  15 custom exception types      │
              │  Pydantic v2 schemas + UTC      │
              │  Request-ID context tracing     │
              └────────────────┬────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                     ▼
 ┌────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
 │   GROQ API     │  │  LOCAL MODELS   │  │      STORAGE        │
 │ llama-3.3-70b  │  │ BAAI/bge-small  │  │  ChromaDB (dense)   │
 │ llama-3.1-8b   │  │ ms-marco-MiniLM │  │  BM25 (sparse)      │
 │ (+ Gemini fb.) │  │ (embed+rerank)  │  │  SQLite × 2 (state  │
 └────────────────┘  └─────────────────┘  │  + HITL queue)      │
                                           └─────────────────────┘
```

---

## Features

### Pillar A — Smart Knowledge Base (RAG)
- **Hybrid retrieval**: BM25 sparse + ChromaDB dense, fused via Reciprocal Rank Fusion (RRF k=60)
- **Cross-encoder reranking**: `ms-marco-MiniLM-L-6-v2` re-scores top-k candidates for precision
- **Dual-stage safety**: deterministic regex refusal layer → LLM-backed router (`fact_only / fee_only / both / refuse`)
- **Grounded answers**: 6-bullet structured output, every fact cited with `[source:doc_id]`
- **Zero hallucination policy**: output validation rejects answers missing source citations

### Pillar B — Review Intelligence & Voice Agent
- **Review ingestion**: Google Play Store scraper (`in.indwealth`) → clean → store
- **Theme extraction**: LLM map-reduce over batches of 100 reviews (fast tier: `llama-3.1-8b-instant`)
- **Trend detection**: week-over-week delta with significance thresholds (≥20% change, ≥5 mentions), pure pandas + scipy — no LLM
- **Weekly pulse**: ≤250-word summary + exactly 3 action items, Pydantic-validated at schema level
- **Voice agent**: 7-state finite state machine (GREETING → BOOKED), generates booking codes `IND-{THEME}-{DATE}-{SEQ}`; booking completion prompts for a separate confirmation email (independent of login credentials)

### Pillar C — Human-in-the-Loop Operations
- **HITL approval queue**: SQLite-backed pending-ops store with WAL mode; ops only execute after human approval
- **Briefing cards**: advisor pre-meeting brief auto-generated from pulse + booking context
- **Google integrations**: Calendar hold, Gmail draft, Google Docs append — all staged for approval via MCP tool definitions
- **Idempotency**: every operation has a booking-code-keyed idempotency lock; duplicate submissions silently deduplicated

### Core Infrastructure
- **LLM reliability**: circuit breaker (5 failures / 60 s window → 30 s open), tenacity retry with exponential backoff, 30 s per-call timeout
- **Structured logging**: Loguru with request-ID context injection; JSON-line format for log aggregation pipelines
- **Schema layer**: 6 Pydantic v2 modules, UTC-enforced datetime, `extra="forbid"` on all models, 78 schema tests
- **Eval framework**: 35 golden RAG questions + 16 adversarial safety prompts + 3 UX assertions; LLM-as-judge scoring via Groq; parallelised with `ThreadPoolExecutor`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **UI** | Streamlit 1.56+ · audio-recorder-streamlit |
| **LLM (primary)** | Groq API · llama-3.3-70b-versatile |
| **LLM (fast tier)** | Groq API · llama-3.1-8b-instant |
| **LLM (fallback)** | Gemini 2.5 Flash Lite (optional) |
| **Embeddings** | sentence-transformers · BAAI/bge-small-en-v1.5 |
| **Reranker** | sentence-transformers · cross-encoder/ms-marco-MiniLM-L-6-v2 |
| **Vector DB** | ChromaDB (persistent) |
| **Sparse index** | bm25s |
| **Structured output** | Instructor 1.8+ · Pydantic v2 |
| **Data processing** | pandas · numpy · scipy |
| **PDF parsing** | docling |
| **Storage** | SQLite (WAL) · diskcache |
| **Google APIs** | google-api-python-client · OAuth 2.0 |
| **Logging** | Loguru |
| **HTTP** | httpx |
| **Retry/resilience** | tenacity |
| **Runtime** | Python 3.12 · uv |
| **Testing** | pytest · pytest-cov · syrupy |
| **Linting** | ruff · pyright (basic) |

---

## Quick Start

**Prerequisites**: Python 3.12+, [uv](https://docs.astral.sh/uv/), a [Groq API key](https://console.groq.com/)

```bash
# 1. Clone and install
git clone <repo-url>
cd "FINAL CAPSTONE PROJECT"
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env and set GROQ_API_KEY=<your-key>

# 3. Verify schema layer (78 tests, no API calls)
uv run pytest tests/ -q

# 4. Ingest the knowledge base
uv run python scripts/ingest_kb.py

# 5. Launch the dashboard
uv run streamlit run app.py
```

**Run the full eval suite** (requires Groq API key, ~20–30 seconds with parallelisation):
```bash
uv run python scripts/run_all_evals.py
# Results → evals/rag_eval_results.json
#            evals/safety_eval_results.json
#            evals/ux_eval_results.json
#            evals/EVALS.md
```

---

## Project Structure

```
.
├── app.py                    # Streamlit entry point
├── config.py                 # Pydantic settings (GROQ, Gemini, paths)
├── conftest.py               # pytest fixtures
├── core/                     # Foundation: LLMClient, logger, exceptions
├── pillars/
│   ├── pillar_a_knowledge/   # RAG: safety, router, retriever, reranker, answerer
│   ├── pillar_b_voice/       # Voice FSM, theme extraction, trends, pulse
│   └── pillar_c_hitl/        # HITL queue, Google APIs, MCP tools, briefing cards
├── schemas/                  # Pydantic v2: rag, pulse, booking, hitl, eval (78 tests)
├── ui/tabs/                  # One file per tab (tab_a … tab_e)
├── evals/                    # golden_dataset.json, adversarial_dataset.json, judges
├── scripts/                  # Pipeline runners, ingestion, smoke tests
├── data/
│   ├── chroma_db/            # ChromaDB persistent store
│   ├── bm25_index/           # BM25 corpus + vocabulary
│   ├── factsheets/           # SBI MF scheme docs (markdown + raw)
│   ├── fees/                 # Exit load & expense schedules
│   └── reviews/              # INDmoney Play Store reviews
├── docs/                     # SOURCES.md, ARCHITECTURE.md, design docs
└── logs/                     # app.log · app.jsonl · system_errors.log
```

---

## Evaluation Framework

| Suite | Cases | Scoring method | Pass threshold |
|-------|-------|---------------|----------------|
| RAG Faithfulness | 35 golden questions | LLM-as-judge (Groq Llama) — facts traceable to cited sources | ≥ 0.50 per question |
| RAG Relevance | 35 golden questions | LLM-as-judge — answer covers expected concepts | ≥ 0.50 per question |
| Safety Refusal | 16 adversarial prompts | Deterministic safety layer + `ask()` refused flag | **100% required** |
| UX Pulse | 3 assertions | Word count ≤250, actions = 3, voice theme mentioned | 3 / 3 |

Questions span three types: `fact_only` (24), `combined` (7), `fee_only` (4).  
Adversarial categories: `investment_advice` (11), `pii_request` (5).  
All evals run in parallel via `ThreadPoolExecutor` (RAG: 4 workers, Safety: 4 workers); total runtime ≈ 20–30 s.

```bash
uv run python scripts/run_all_evals.py   # populate evals/EVALS.md
```

---

## Data Sources

All fund data is sourced from official public AMC and regulatory pages. No data is synthesised or fabricated. Status last verified 2026-04-24. Two known broken links noted below.

### SBI Asset Management Company — Fund Scheme Pages

| # | Title | URL | Status |
|---|-------|-----|--------|
| 1 | SBI Large Cap Fund (formerly SBI Bluechip Fund) | https://www.sbimf.com/sbimf-scheme-details/sbi-large-cap-fund-(formerly-known-as-sbi-bluechip-fund)-43 | ✅ OK |
| 2 | SBI Small Cap Fund | https://www.sbimf.com/sbimf-scheme-details/sbi-small-cap-fund-329 | ✅ OK |
| 3 | SBI Equity Hybrid Fund | https://www.sbimf.com/sbimf-scheme-details/sbi-equity-hybrid-fund-5 | ✅ OK |
| 4 | SBI Midcap Fund | https://www.sbimf.com/sbimf-scheme-details/sbi-midcap-fund-34 | ✅ OK |
| 5 | SBI ELSS Tax Saver Fund (formerly SBI Long Term Equity Fund) | https://www.sbimf.com/sbimf-scheme-details/sbi-elss-tax-saver-fund-(formerly-known-as-sbi-long-term-equity-fund)-3 | ✅ OK |
| 6 | SBI MF Homepage | https://www.sbimf.com | ✅ OK |
| 7 | SBI MF FAQ | https://www.sbimf.com/faq | ✅ OK |
| 8 | SBI MF — Scheme Information Documents (SID) & KIM | https://www.sbimf.com/offer-document-sid-kim | ✅ OK |

### SEBI — Regulatory Documents

| # | Title | URL | Status |
|---|-------|-----|--------|
| 9 | SEBI Mutual Fund Regulations 1996 (last amended Sep 2019) | https://www.sebi.gov.in/legal/regulations/sep-2019/securities-and-exchange-board-of-india-mutual-funds-regulations-1996-last-amended-on-september-23-2019-_41350.html | ✅ OK |
| 10 | SEBI Riskometer Circular (SEBI/IMD/CIR No.9) | https://www.sebi.gov.in/sebi_data/attachdocs/1337083696184.pdf | ✅ OK |
| 11 | SEBI Investor Education — Exit Load | https://investor.sebi.gov.in/knowledge-centre/exit-load.html | ⚠️ 404 (page moved) |

### AMFI — Investor Education & KYC

| # | Title | URL | Status |
|---|-------|-----|--------|
| 12 | AMFI Investor Awareness Program | https://www.amfiindia.com/investor/investor-awareness-program | ✅ OK |
| 13 | AMFI — Introduction to Mutual Funds | https://www.amfiindia.com/investor/knowledge-center-info?zoneName=IntroductionMutualFunds | ✅ OK |
| 14 | AMFI — SIP Guidance | https://www.amfiindia.com/investor/become-mf-distributor?zoneName=sip | ✅ OK |
| 15 | AMFI — KYC Requirements | https://www.amfiindia.com/kyc | ✅ OK |

### Income Tax India

| # | Title | URL | Status |
|---|-------|-----|--------|
| 16 | Income Tax — Section 80C (ELSS deduction) | https://www.incometaxindia.gov.in/section-80-c | ✅ OK |
| 17 | Income Tax — Capital Gains on Mutual Funds | https://www.incometaxindia.gov.in/sale-of-shares | ✅ OK |

### CAMS — Registrar & Transfer Agent

| # | Title | URL | Status |
|---|-------|-----|--------|
| 18 | CAMS Investor Services | https://www.camsonline.com/Investors | ✅ OK |

### Review & Reference Data

| # | Title | URL | Status |
|---|-------|-----|--------|
| 19 | INDmoney App — Google Play Store | https://play.google.com/store/apps/details?id=in.indwealth | ✅ OK |
| 20 | INDmoney Help — Exit Load Definition | https://www.indmoney.com/help/mutual-funds/what-is-exit-load | ⚠️ 403 (auth required) |

### API & Model Documentation

| # | Title | URL |
|---|-------|-----|
| 21 | Groq API Documentation | https://console.groq.com/docs/overview |
| 22 | Groq — llama-3.3-70b-versatile model card | https://console.groq.com/docs/models |
| 23 | Google Gemini API Reference | https://ai.google.dev/api/rest |
| 24 | Google Calendar API | https://developers.google.com/calendar/api/v3/reference |
| 25 | Gmail API | https://developers.google.com/gmail/api/reference/rest |
| 26 | Google Docs API | https://developers.google.com/docs/api/reference/rest |

### Model Repositories (HuggingFace)

| # | Model | URL |
|---|-------|-----|
| 27 | BAAI/bge-small-en-v1.5 (embeddings) | https://huggingface.co/BAAI/bge-small-en-v1.5 |
| 28 | cross-encoder/ms-marco-MiniLM-L-6-v2 (reranker) | https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2 |

### Key Libraries & Frameworks

| # | Library | URL |
|---|---------|-----|
| 29 | ChromaDB | https://docs.trychroma.com |
| 30 | bm25s | https://github.com/xhluca/bm25s |
| 31 | Sentence Transformers | https://www.sbert.net |
| 32 | Instructor (structured LLM output) | https://python.useinstructor.com |
| 33 | Streamlit | https://docs.streamlit.io |
| 34 | Pydantic v2 | https://docs.pydantic.dev/latest |
| 35 | Loguru | https://loguru.readthedocs.io |
| 36 | Tenacity | https://tenacity.readthedocs.io |
| 37 | google-play-scraper | https://github.com/JoMingyu/google-play-scraper |
| 38 | docling (PDF parsing) | https://github.com/DS4SD/docling |

---

## Compliance Checklist

- [x] All fund data sourced from official public AMC/regulatory URLs (verified in `data/manifests/source_manifest.json`)
- [x] No synthetic, fabricated, or hallucinated fund figures
- [x] Only 5 permitted SBI schemes in knowledge base
- [x] Investment advice refusals: deterministic regex + LLM router double-checked
- [x] PII refusals: deterministic regex catches email, phone, PAN, Aadhaar, account number requests
- [x] Safety layer runs before any LLM call (zero API cost on adversarial inputs)
- [x] HITL gate: no Google Calendar/Gmail/Docs write without human approval
- [x] All operations idempotent (booking-code-keyed deduplication)
- [x] UTC-enforced timestamps on all schema models
- [x] Structured logging with request-ID tracing on every LLM call
- [x] Circuit breaker prevents runaway API spend on outages
- [x] Schema contracts immutable after Phase 1 (protected by `conftest.py`)

---

## Built By

**Aarti Dhavare** — AI/ML Product Engineering capstone project, 2026.
