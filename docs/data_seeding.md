# Data Seeding Design — Phase 2

## Purpose

Build a real-data corpus that feeds three downstream consumers:

1. **RAG retrieval** — factsheets and fee docs are chunked and indexed so the assistant can answer fund-specific questions with cited passages.
2. **Pulse pipeline** — structured fields extracted from factsheets (NAV, AUM, expense ratio, exit load) populate the pulse Pydantic schemas defined in Phase 1.
3. **Evals harness** — reviews, factsheets, and fee docs provide ground-truth inputs for the evaluation suite so every quality gate runs against data sourced from authorised public URLs.

All content in `data/` must be traceable to a real public URL fetched in the same session that produced the file. No content is invented, inferred, or carried over from model training knowledge.

---

## Sources of Truth

| Data type | Primary source | Secondary / cross-check |
|---|---|---|
| Fund factsheets (PDF) | `sbimf.com` — monthly factsheet downloads page | AMFI fund-house disclosure portal |
| Scheme-level fee data | `sebi.gov.in` — TER circulars and disclosure filings | `amfiindia.com` — NAV and scheme data files |
| Regulatory references | `sebi.gov.in` — LODR / MF Regulations / circulars | `amfiindia.com` — best-practice circulars |
| App reviews | Google Play Store — INDmoney app listing | Scraped via `google-play-scraper` library |

### In-scope funds (exact names, no others)

- SBI Bluechip Fund
- SBI Small Cap Fund
- SBI Equity Hybrid Fund
- SBI Midcap Fund
- SBI Long Term Equity Fund (ELSS)

Any other fund house or scheme is out of scope and must not appear in any file under `data/`.

---

## Factsheet Markdown Template

Each PDF downloaded from `sbimf.com` is converted to one Markdown file stored in `data/factsheets/markdown/`. Every file must contain exactly the following seven H2 sections in order.

```
## Fund Overview
## Key Facts
## Expense Ratio
## Exit Load
## Minimum Investment
## Top Holdings
## Taxation
```

### Section content rules

**Fund Overview** — fund name (exact AMFI name), fund category (SEBI categorisation), fund objective copied verbatim from the factsheet, benchmark index name.

**Key Facts** — AUM (₹ crore, as of factsheet date), NAV (regular and direct plan, as of factsheet date), fund manager name(s) as printed on the factsheet, inception date, ISIN for regular and direct growth options.

**Expense Ratio** — TER for regular plan and direct plan as disclosed in the factsheet, expressed as `X.XX%`, factsheet date used as the as-of date.

**Exit Load** — verbatim exit-load clause from the factsheet (e.g., "1% if redeemed within 1 year of allotment, Nil thereafter"). If none, write `Nil`.

**Minimum Investment** — lump-sum minimum (₹), SIP minimum (₹), additional purchase minimum (₹) as printed.

**Top Holdings** — up to ten holdings listed as a Markdown table with columns `Security`, `% of NAV`; values copied from the factsheet portfolio disclosure.

**Taxation** — equity / hybrid classification per SEBI, applicable LTCG threshold and rate, STCG rate, dividend taxation note — sourced from the factsheet or the accompanying KIM.

---

## Fee Doc Markdown Template

Each fee-topic document is stored in `data/fees/`. Every file must contain exactly the following six H2 sections in order.

```
## What It Is
## Who Is Involved
## How It Is Calculated
## Worked Example
## Edge Cases
## Regulatory References
```

### Section content rules

**What It Is** — plain-language definition of the fee or charge; one to three sentences; no invented content.

**Who Is Involved** — the parties (AMC, distributor, SEBI, investor) and their roles relative to this fee.

**How It Is Calculated** — formula or method as described in the applicable SEBI circular or AMFI guidance; cite the document title and date.

**Worked Example** — a numeric illustration derived from real disclosed figures (TER, AUM, NAV) taken from the factsheet or SEBI filing. No invented numbers.

**Edge Cases** — documented exceptions: direct vs. regular plan differences, debt vs. equity TER caps, ELSS lock-in interactions, exit-load waiver conditions. Source each edge case to a named regulatory document.

**Regulatory References** — bulleted list of exact document titles, dates, and URLs from `sebi.gov.in` or `amfiindia.com` that govern this fee.

---

## Reviews Pipeline

```
Google Play Store (INDmoney listing)
        |
        v
google-play-scraper  (scripts/scrape_reviews.py)
        |  raw JSON — reviewer handle, rating, date, text
        v
Clean pass  (drop duplicates, drop non-English, normalise whitespace)
        |
        v
PII masking  (see rules below)
        |
        v
data/reviews/indmoney_reviews.csv
  columns: review_id, rating, date, text_clean, pii_masked (bool flag)
```

### PII Masking Rules

All masking is applied to the `text_clean` field before the row is written to CSV. A `pii_masked` boolean column is set to `True` if any substitution was made.

| PII type | Detection pattern | Replacement |
|---|---|---|
| Email address | `[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}` | `[EMAIL]` |
| Indian mobile number | `(\+91[\-\s]?)?[6-9]\d{9}` | `[PHONE]` |
| PAN card number | `[A-Z]{5}[0-9]{4}[A-Z]` | `[PAN]` |
| Name-pattern (capitalised two-word sequence adjacent to "my name is" / "I am") | contextual regex on trigger phrases | `[NAME]` |
| Reviewer handle / username | always present in raw scrape field | `[REDACTED]` (field is never written to CSV in unmasked form) |

Masking is one-way; no mapping from replacement token back to original is stored anywhere in the repository.

---

## URL Manifest Quality Bar

The file `data/manifest.json` lists every source URL used to produce content in `data/`. It must satisfy all of the following before Phase 2 is considered complete.

1. **Minimum 20 URLs** — at least 20 distinct entries across factsheets, fee regulatory docs, and the Play Store listing.
2. **All entries live-verified** — every URL in the manifest must have been fetched successfully (HTTP 200 or equivalent) in the same session that added it; the verification timestamp is recorded in the manifest entry.
3. **Required fields per entry**

```json
{
  "url": "https://...",
  "type": "factsheet_pdf | fee_regulatory | reviews_store",
  "fund": "SBI Bluechip Fund | null",
  "fetched_at": "2026-04-24T10:00:00Z",
  "http_status": 200,
  "local_path": "data/factsheets/raw/sbi_bluechip_apr2026.pdf"
}
```

4. **No 404s or redirects to login walls** — if a URL returns anything other than 200 with the expected content type, it is removed from the manifest and the download is retried or escalated.
5. **Reproducibility** — any URL in the manifest must be re-fetchable by anyone running the seed script; URLs behind authentication or bot-blocking are not acceptable.

---

## Validation Gates

`scripts/validate_data.py` must exit with code 0 before Phase 2 is considered complete. The script checks:

1. Every file in `data/factsheets/markdown/` contains all seven required H2 headings in the correct order.
2. Every file in `data/fees/` contains all six required H2 headings in the correct order.
3. `data/reviews/indmoney_reviews.csv` exists, has the expected five columns, and contains at least 50 rows.
4. `data/manifest.json` is valid JSON, has at least 20 entries, and every entry contains the five required fields.
5. No file under `data/` contains the strings `synthetic`, `fictional`, `hypothetical`, `example data`, `sample fund`, `generated`, or `placeholder` (case-insensitive).
6. No fund name outside the five in-scope SBI schemes appears in any file under `data/factsheets/` or `data/fees/`.

A non-zero exit terminates the Phase 2 pipeline and requires manual remediation before any downstream step (RAG indexing, pulse ingestion, eval harness) is run.
