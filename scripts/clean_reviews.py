"""
scripts/clean_reviews.py

Phase 2 Sub-step 5: Clean raw Play Store reviews to a high-quality CSV.
Reads  : data/reviews/raw/indmoney_playstore_raw.json
Outputs: data/reviews/reviews.csv
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.error_logger import log_structured_error
from core.logger import log

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
RAW_JSON = ROOT / "data" / "reviews" / "raw" / "indmoney_playstore_raw.json"
OUT_CSV = ROOT / "data" / "reviews" / "reviews.csv"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# PII patterns
# ---------------------------------------------------------------------------
_RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_RE_PHONE = re.compile(r"(\+?91[\s-]?)?[6-9]\d{9}")
_RE_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_RE_NAME = re.compile(r"(?i)(my name is|i am|this is)\s+([A-Z][a-z]+)")

# Emoji — covers major Unicode emoji blocks
_RE_EMOJI = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002500-\U00002BEF"
    "\U00010000-\U0010FFFF"
    "]+",
    flags=re.UNICODE,
)

_ASCII_LIKE = re.compile(r"[a-zA-Z0-9\s.,!?'\-]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ascii_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(_ASCII_LIKE.findall(text)) / len(text)


def _distinct_word_count(text: str) -> int:
    return len(set(text.lower().split()))


def _strip_emoji(text: str) -> str:
    return _RE_EMOJI.sub("", text)


def _mask_pii(text: str) -> tuple[str, bool]:
    original = text
    text = _RE_EMAIL.sub("[REDACTED]", text)
    text = _RE_PHONE.sub("[REDACTED]", text)
    text = _RE_PAN.sub("[REDACTED]", text)
    text = _RE_NAME.sub(lambda m: m.group(1) + " [REDACTED]", text)
    return text, text != original


def _parse_date(raw: str) -> datetime:
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=datetime.UTC)
    except Exception:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.UTC)
        return dt


def _to_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("clean_reviews: starting pipeline")

    # Step 1 — Load raw JSON
    log.info("Step 1: loading raw JSON from {}", RAW_JSON)
    with RAW_JSON.open(encoding="utf-8") as f:
        raw: list[dict] = json.load(f)
    n_raw = len(raw)
    log.info("  loaded {} reviews", n_raw)

    records: list[dict] = []
    for idx, item in enumerate(raw):
        try:
            dt = _parse_date(str(item.get("at", "")))
        except Exception:
            dt = datetime(1970, 1, 1, tzinfo=datetime.UTC)
        records.append(
            {
                "review_id": item.get("reviewId") or f"r-{idx:05d}",
                "rating": int(item.get("score", 0)),
                "text": str(item.get("content") or ""),
                "app_version": item.get("reviewCreatedVersion") or "unknown",
                "dt": dt,
            }
        )

    # Step 2 — English only (ascii_ratio >= 0.70)
    log.info("Step 2: English filter (ascii_ratio >= 0.70)")
    records = [r for r in records if _ascii_ratio(r["text"]) >= 0.70]
    n_after_english = len(records)
    log.info("  {} reviews remain", n_after_english)

    # Step 3 — Substantive length (>= 50 chars)
    log.info("Step 3: length filter (>= 50 chars)")
    records = [r for r in records if len(r["text"].strip()) >= 50]
    n_after_length = len(records)
    log.info("  {} reviews remain", n_after_length)

    # Step 4 — No gibberish (>= 3 distinct words)
    log.info("Step 4: gibberish filter (>= 3 distinct words)")
    records = [r for r in records if _distinct_word_count(r["text"]) >= 3]
    n_after_gibberish = len(records)
    log.info("  {} reviews remain", n_after_gibberish)

    # Step 5 — No emoji-only (strip emoji, remaining >= 20 chars)
    log.info("Step 5: emoji-only filter")
    records = [r for r in records if len(_strip_emoji(r["text"]).strip()) >= 20]
    n_after_emoji = len(records)
    log.info("  {} reviews remain", n_after_emoji)

    # Step 6 — Rating split
    log.info("Step 6: splitting into negative/positive pools")
    neg_pool = [r for r in records if 1 <= r["rating"] <= 3]
    pos_pool = [r for r in records if 4 <= r["rating"] <= 5]
    n_neg_raw = len(neg_pool)
    n_pos_raw = len(pos_pool)
    log.info("  negative pool: {}, positive pool: {}", n_neg_raw, n_pos_raw)

    # Step 7 — Dedup within each pool
    log.info("Step 7: dedup within each pool")

    def dedup(pool: list[dict]) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for r in pool:
            if r["text"] not in seen:
                seen.add(r["text"])
                out.append(r)
        return out

    neg_pool = dedup(neg_pool)
    pos_pool = dedup(pos_pool)
    n_neg_dedup = len(neg_pool)
    n_pos_dedup = len(pos_pool)
    log.info("  after dedup — negative: {}, positive: {}", n_neg_dedup, n_pos_dedup)

    # Step 8 — PII masking
    log.info("Step 8: PII masking")
    pii_count = 0
    for pool in (neg_pool, pos_pool):
        for r in pool:
            masked, changed = _mask_pii(r["text"])
            r["text"] = masked
            if changed:
                pii_count += 1
    log.info("  {} reviews had PII redacted", pii_count)

    # Step 9 — Sample final 300
    log.info("Step 9: sampling final 300 rows")
    TARGET = 300
    TARGET_NEG = 250
    TARGET_POS = 50

    neg_pool.sort(key=lambda r: r["dt"], reverse=True)
    pos_pool.sort(key=lambda r: r["dt"], reverse=True)

    if len(neg_pool) >= TARGET_NEG and len(pos_pool) >= TARGET_POS:
        selected_neg = neg_pool[:TARGET_NEG]
        selected_pos = pos_pool[:TARGET_POS]
    elif len(neg_pool) < TARGET_NEG:
        selected_neg = neg_pool[:]
        fill = TARGET - len(selected_neg)
        selected_pos = pos_pool[:fill]
    else:
        selected_pos = pos_pool[:]
        fill = TARGET - len(selected_pos)
        selected_neg = neg_pool[:fill]

    final = selected_neg + selected_pos
    n_final = len(final)
    log.info("  final sample: {} rows", n_final)

    if n_final < 200:
        log.error("Final row count {} is below minimum threshold of 200", n_final)
        log_structured_error(
            phase="Phase-2 Sub-step 5",
            module="scripts.clean_reviews",
            error_type="Safety",
            description="Final CSV row count below minimum acceptable threshold",
            input_val=str(RAW_JSON),
            expected=">=200 rows after filtering",
            actual=f"{n_final} rows",
            fix="Check filtering thresholds or re-scrape more reviews",
            status="Pending",
        )
        raise SystemExit(1)

    # Step 10 — Week column (median split on full date range)
    log.info("Step 10: computing week column")
    all_dates = [r["dt"] for r in final]
    min_dt = min(all_dates)
    max_dt = max(all_dates)
    median_dt = min_dt + (max_dt - min_dt) / 2
    span_weeks = (max_dt - min_dt).days / 7
    log.info("  date range: {} to {}", _to_iso(min_dt), _to_iso(max_dt))
    log.info("  span: {:.1f} weeks, median split at {}", span_weeks, _to_iso(median_dt))

    week_a_count = 0
    week_b_count = 0
    rows: list[dict] = []
    for r in final:
        week = "week_a" if r["dt"] <= median_dt else "week_b"
        if week == "week_a":
            week_a_count += 1
        else:
            week_b_count += 1
        rows.append(
            {
                "review_id": r["review_id"],
                "user_handle": "[REDACTED]",
                "rating": r["rating"],
                "theme": "unclassified",
                "week": week,
                "review_date": _to_iso(r["dt"]),
                "review_text": r["text"],
                "app_version": r["app_version"],
                "platform": "Android",
            }
        )

    # Step 11 — Write CSV
    log.info("Step 11: writing CSV to {}", OUT_CSV)
    fieldnames = [
        "review_id",
        "user_handle",
        "rating",
        "theme",
        "week",
        "review_date",
        "review_text",
        "app_version",
        "platform",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    log.info("  wrote {} rows to {}", n_final, OUT_CSV)

    # Step 12 — Summary table
    print("\n" + "=" * 55)
    print("  CLEAN REVIEWS SUMMARY")
    print("=" * 55)
    print(f"  Raw reviews loaded:        {n_raw}")
    print(f"  After English filter:      {n_after_english}")
    print(f"  After length filter:       {n_after_length}")
    print(f"  After gibberish filter:    {n_after_gibberish}")
    print(f"  After emoji-only filter:   {n_after_emoji}")
    print(f"  Negative pool (1-3 stars): {n_neg_raw}")
    print(f"  Positive pool (4-5 stars): {n_pos_raw}")
    print(f"  After dedup (negative):    {n_neg_dedup}")
    print(f"  After dedup (positive):    {n_pos_dedup}")
    print(f"  PII redactions made:       {pii_count}")
    print(f"  Final CSV rows:            {n_final}")
    print(f"  Date range:                {_to_iso(min_dt)} to {_to_iso(max_dt)}")
    print(f"  Date span:                 {span_weeks:.1f} weeks")
    print(f"  week_a count:              {week_a_count}")
    print(f"  week_b count:              {week_b_count}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
