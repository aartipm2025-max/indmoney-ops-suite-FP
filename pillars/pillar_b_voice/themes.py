"""
Theme extraction from Play Store reviews using Groq LLM (map-reduce).

Stage 1 (map)  — batch 50 reviews → llama-3.1-8b-instant → ≤5 themes each
Stage 2 (reduce) — merge similar themes, sum counts, keep best quote
"""

import json
import logging
import sys
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — allow running from any working directory
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402

from core.error_logger import log_from_exception  # noqa: E402
from core.llm_client import LLMClient  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BATCH_SIZE = 50
MAX_THEMES_PER_BATCH = 5
TOP_N = 5

SYSTEM_PROMPT = (
    "You are a product review analyst. Given these app reviews, identify the main "
    "complaint/praise themes. For each theme, provide: theme_name (short label like "
    "'Login Issues', 'Slow Updates', 'Good Support'), count (how many reviews in "
    "this batch mention it), and one verbatim quote that best represents it. "
    'Return JSON array ONLY: [{"theme": "...", "count": N, "quote": "..."}]. '
    f"Max {MAX_THEMES_PER_BATCH} themes per batch. NO explanation."
)

# ---------------------------------------------------------------------------
# FIXED JSON PARSER (CRITICAL FIX)
# ---------------------------------------------------------------------------
def _parse_json_response(raw: str) -> list[dict]:
    """
    Robust JSON extractor:
    - Handles markdown fences
    - Extracts ONLY first valid JSON array
    - Ignores extra text before/after
    """
    text = raw.strip()

    # Remove markdown code blocks
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            if "[" in part and "]" in part:
                text = part.strip()
                break

    # Extract FIRST JSON array only
    match = re.search(r"\[\s*{.*?}\s*\]", text, re.DOTALL)
    if not match:
        raise ValueError("No valid JSON array found in LLM response")

    json_str = match.group(0)

    return json.loads(json_str)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _themes_are_similar(a: str, b: str) -> bool:
    la, lb = a.lower().strip(), b.lower().strip()
    return la in lb or lb in la

def _merge_batch_themes(all_batch_themes: list[list[dict]]) -> list[dict]:
    merged: list[dict] = []

    for batch in all_batch_themes:
        for item in batch:
            theme_name = item.get("theme") or item.get("theme_name", "Unknown")
            count = int(item.get("count", 1))
            quote = item.get("quote", "")

            matched = False
            for existing in merged:
                if _themes_are_similar(existing["theme"], theme_name):
                    existing["count"] += count
                    if len(quote) > len(existing["quote"]):
                        existing["quote"] = quote
                    matched = True
                    break

            if not matched:
                merged.append(
                    {
                        "theme": theme_name,
                        "count": count,
                        "quote": quote,
                        "review_ids": [],
                    }
                )

    merged.sort(key=lambda t: t["count"], reverse=True)
    return merged[:TOP_N]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def extract_themes(reviews_csv_path: Path) -> list[dict]:
    df = pd.read_csv(reviews_csv_path)
    logger.info("Loaded %d reviews from %s", len(df), reviews_csv_path)

    llm = LLMClient()
    all_batch_themes: list[list[dict]] = []

    review_texts = df["review_text"].astype(str).tolist()
    review_ids = df["review_id"].astype(str).tolist()

    batches = [
        review_texts[i : i + BATCH_SIZE]
        for i in range(0, len(review_texts), BATCH_SIZE)
    ]
    batch_ids = [
        review_ids[i : i + BATCH_SIZE]
        for i in range(0, len(review_ids), BATCH_SIZE)
    ]

    logger.info("Processing %d batches", len(batches))

    for idx, (batch_texts, batch_review_ids) in enumerate(zip(batches, batch_ids)):
        user_message = "\n".join(batch_texts)

        try:
            raw = llm.chat(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                model="fast",
                temperature=0.1,
                max_tokens=1024,
            )

            try:
                themes = _parse_json_response(raw)
            except Exception:
                # Retry once with stricter settings
                logger.warning("Retrying batch %d with strict mode", idx + 1)
                raw = llm.chat(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    model="fast",
                    temperature=0.0,
                    max_tokens=1024,
                )
                themes = _parse_json_response(raw)

            for t in themes:
                t.setdefault("review_ids", [])
                t["review_ids"].extend(batch_review_ids[:5])

            all_batch_themes.append(themes)
            logger.info("Batch %d/%d success", idx + 1, len(batches))

        except Exception as exc:
            log_from_exception(
                phase="4 — Pulse Pipeline",
                module="pillars/pillar_b_voice/themes.py",
                exc=exc,
                input_val=f"batch={idx + 1}/{len(batches)}",
                fix="Skipping batch, continuing",
            )
            logger.warning("Batch %d failed, skipping: %s", idx + 1, exc)
            continue

    if not all_batch_themes:
        logger.error("All batches failed")
        return []

    merged = _merge_batch_themes(all_batch_themes)
    logger.info("Merged into %d themes", len(merged))
    return merged