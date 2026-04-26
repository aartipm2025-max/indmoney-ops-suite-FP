# Theme Classification & Pulse Pipeline — Design Document

## Purpose

Analyse ~300 real Play Store reviews scraped for the INDmoney app, extract recurring complaint/praise themes, detect week-over-week trends, and produce a concise weekly **Product Pulse** report that the ops team can act on immediately.

## Pipeline

```
reviews.csv  →  Theme Extraction (8B)  →  Trend Detection (stats)  →  Pulse Generation (70B)
```

### Stage 1 — Theme Extraction (`themes.py`)

Two-phase **map-reduce** over the review corpus.

| Phase | Detail |
|-------|--------|
| **Map** | Reviews are batched in groups of 50. Each batch is sent to `llama-3.1-8b-instant` (Groq, fast tier) with a prompt that asks for ≤ 5 themes, each with a count and one verbatim quote. |
| **Reduce** | Batch results are merged: themes whose lowercased names are substrings of one another are unified, counts are summed, and the longest quote is kept per theme. The top 5 themes (by total count) are returned. |

### Stage 2 — Trend Detection (`trends.py`)

No LLM calls — pure pandas + arithmetic.

For each theme the pipeline counts how many reviews in `week_a` vs `week_b` contain the theme keyword (case-insensitive substring match). It then computes:

* **abs_delta** = week_b − week_a
* **pct_delta** = abs_delta / week_a × 100
* **direction**: `up` / `down` / `flat`
* **is_significant**: |pct_delta| ≥ 20 AND min(week_a, week_b) ≥ 5

### Stage 3 — Pulse Generation (`pulse.py`)

The top 3 themes (with trend arrows and one real user quote each) are sent to `llama-3.3-70b-versatile` (primary tier). The prompt enforces:

* ≤ 250 words total
* Exactly 3 action items
* Structured sections: Summary · Top Themes · User Voices · Action Items

If the first response exceeds 250 words, one automatic retry is made with an explicit word-count reminder.

### Output

A dict containing the pulse summary text, top 3 themes with trends, 3 extracted user quotes, 3 action items, word count, and an ISO-8601 generation timestamp.
