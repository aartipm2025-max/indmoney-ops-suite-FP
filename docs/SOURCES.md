# Data Sources & References

All fund data, regulatory content, and review data used in this project is sourced from official public URLs. No data is synthesised, fabricated, or generated. This document lists every external source referenced.

Source verification status is tracked in `data/manifests/source_manifest.json` (last verified 2026-04-24).

---

## 1. SBI Asset Management Company — Fund Scheme Pages

Primary source for factsheets: key facts, NAV, AUM, benchmark, fund manager, holdings, exit loads, expense ratios, minimum investments, taxation, and scheme objectives.

| # | Title | URL | Status |
|---|-------|-----|--------|
| 1 | SBI Large Cap Fund (formerly SBI Bluechip Fund) | https://www.sbimf.com/sbimf-scheme-details/sbi-large-cap-fund-(formerly-known-as-sbi-bluechip-fund)-43 | ✅ OK |
| 2 | SBI Small Cap Fund | https://www.sbimf.com/sbimf-scheme-details/sbi-small-cap-fund-329 | ✅ OK |
| 3 | SBI Equity Hybrid Fund | https://www.sbimf.com/sbimf-scheme-details/sbi-equity-hybrid-fund-5 | ✅ OK |
| 4 | SBI Midcap Fund | https://www.sbimf.com/sbimf-scheme-details/sbi-midcap-fund-34 | ✅ OK |
| 5 | SBI ELSS Tax Saver Fund (formerly SBI Long Term Equity Fund) | https://www.sbimf.com/sbimf-scheme-details/sbi-elss-tax-saver-fund-(formerly-known-as-sbi-long-term-equity-fund)-3 | ✅ OK |

### SBI MF Supporting Pages

| # | Title | URL | Status |
|---|-------|-----|--------|
| 6 | SBI MF Homepage | https://www.sbimf.com | ✅ OK |
| 7 | SBI MF FAQ | https://www.sbimf.com/faq | ✅ OK |
| 8 | SBI MF — Scheme Information Documents (SID) & KIM | https://www.sbimf.com/offer-document-sid-kim | ✅ OK |

---

## 2. SEBI — Regulatory Documents

| # | Title | URL | Status |
|---|-------|-----|--------|
| 9 | SEBI Mutual Fund Regulations 1996 (last amended Sep 2019) | https://www.sebi.gov.in/legal/regulations/sep-2019/securities-and-exchange-board-of-india-mutual-funds-regulations-1996-last-amended-on-september-23-2019-_41350.html | ✅ OK |
| 10 | SEBI Riskometer Circular (SEBI/IMD/CIR No.9) | https://www.sebi.gov.in/sebi_data/attachdocs/1337083696184.pdf | ✅ OK |
| 11 | SEBI Investor Education — Exit Load | https://investor.sebi.gov.in/knowledge-centre/exit-load.html | ⚠️ 404 (page moved) |

> Note: Item 11 was listed as the regulatory reference for exit load mechanics in `elss_exit_load.md`. The content was captured before the page was reorganised. The SEBI MF Regulations (item 9) remain the authoritative source.

---

## 3. AMFI — Investor Education & KYC

| # | Title | URL | Status |
|---|-------|-----|--------|
| 12 | AMFI Investor Awareness Program | https://www.amfiindia.com/investor/investor-awareness-program | ✅ OK |
| 13 | AMFI — Introduction to Mutual Funds | https://www.amfiindia.com/investor/knowledge-center-info?zoneName=IntroductionMutualFunds | ✅ OK |
| 14 | AMFI — SIP Guidance | https://www.amfiindia.com/investor/become-mf-distributor?zoneName=sip | ✅ OK |
| 15 | AMFI — KYC Requirements | https://www.amfiindia.com/kyc | ✅ OK |

---

## 4. Income Tax India — Tax Regulations

| # | Title | URL | Status |
|---|-------|-----|--------|
| 16 | Income Tax — Section 80C (ELSS deduction) | https://www.incometaxindia.gov.in/section-80-c | ✅ OK |
| 17 | Income Tax — Capital Gains on Mutual Funds | https://www.incometaxindia.gov.in/sale-of-shares | ✅ OK |

---

## 5. CAMS — Registrar & Transfer Agent

| # | Title | URL | Status |
|---|-------|-----|--------|
| 18 | CAMS Investor Services | https://www.camsonline.com/Investors | ✅ OK |

---

## 6. Review Data Source

| # | Title | URL | Status |
|---|-------|-----|--------|
| 19 | INDmoney App — Google Play Store | https://play.google.com/store/apps/details?id=in.indwealth | ✅ OK |
| 20 | INDmoney Help — Exit Load Definition | https://www.indmoney.com/help/mutual-funds/what-is-exit-load | ⚠️ 403 (auth required) |

Review data was collected using the `google-play-scraper` Python library (public API) and stored at `data/reviews/raw/indmoney_playstore_raw.json`. No login or scraping of authenticated content was performed.

---

## 7. API & Model Documentation

| # | Title | URL |
|---|-------|-----|
| 21 | Groq API Documentation | https://console.groq.com/docs/overview |
| 22 | Groq — llama-3.3-70b-versatile model card | https://console.groq.com/docs/models |
| 23 | Google Gemini API Reference | https://ai.google.dev/api/rest |
| 24 | Google Calendar API | https://developers.google.com/calendar/api/v3/reference |
| 25 | Gmail API | https://developers.google.com/gmail/api/reference/rest |
| 26 | Google Docs API | https://developers.google.com/docs/api/reference/rest |

---

## 8. Model Repositories (HuggingFace)

| # | Model | URL |
|---|-------|-----|
| 27 | BAAI/bge-small-en-v1.5 (embeddings) | https://huggingface.co/BAAI/bge-small-en-v1.5 |
| 28 | cross-encoder/ms-marco-MiniLM-L-6-v2 (reranker) | https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2 |

---

## 9. Key Libraries & Frameworks

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

## Verification

Run `python scripts/generate_source_manifest.py` to re-verify all URLs and update `data/manifests/source_manifest.json`.

Two known broken links:
- **Item 11** (SEBI exit load page) — SEBI has reorganised their investor education portal; content captured before removal
- **Item 20** (INDmoney help page) — Returns HTTP 403; referenced as external context only, not used as a data source
