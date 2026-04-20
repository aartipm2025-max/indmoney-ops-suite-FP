# Running Improvement Log

---

## Day 0 — Seeded from Research Report v4 Recommendations

### Post-v1 Candidates (Rejected for 9-Day Scope)

These improvements were identified during research and design but are explicitly out of scope for the initial 9-day build. They are documented here so they are not forgotten and can be prioritised for a v2.

| Candidate | Rationale for Deferral | Estimated Effort |
|---|---|---|
| FastAPI backend extraction | Requires designing REST API contracts, migration of all pillar logic, and a separate frontend. Valuable for production but premature for a solo proof-of-concept. | ~3 days |
| Redis queue + Celery workers | Needed only if background tasks (Google API calls) must be durable and fault-tolerant at scale. SQLite outbox is sufficient for single-user. | ~2 days |
| Multi-hop RAG / query decomposition | Would improve faithfulness on complex multi-fund queries. Requires a planning LLM call per query, adding latency and complexity. Defer until golden dataset reveals this as the binding constraint. | ~1.5 days |
| Continuous eval via GitHub Actions | Automated CI eval pipeline would catch regressions on every commit. Valuable long-term; deferred to stretch goal on Day 8 if time permits. | ~1 day |
| RAG explainability drawer | Side-panel in UI showing retrieved chunks and reranker scores, to build user trust. Good UX addition; deferred to stretch Day 7. | ~0.5 days |
| Inline confidence scoring | Attach a confidence estimate to each answer bullet. Requires calibrated uncertainty from the judge model. Deferred to stretch Day 8. | ~1 day |

---

## Added During Build

*(Claude Code appends entries here as bugs, design decisions, and scope changes are encountered during the build.)*
