"""
Theme extraction from Play Store reviews using Groq LLM (map-reduce).

Stage 1 (map)  — batch 50 reviews → llama-3.1-8b-instant → ≤5 themes each
Stage 2 (reduce) — merge similar themes, sum counts, keep best quote
"""

import json
import logging
import sys
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
BATCH_SIZE = 100
MAX_THEMES_PER_BATCH = 5
TOP_N = 5

SYSTEM_PROMPT = (
    "You are a product review analyst. Given these app reviews, identify the main "
    "complaint/praise themes. For each theme, provide: theme_name (short label like "
    "'Login Issues', 'Slow Updates', 'Good Support'), count (how many reviews in "
    "this batch mention it), and one verbatim quote that best represents it. "
    'Return JSON array: [{"theme": "...", "count": N, "quote": "..."}]. '
    f"Max {MAX_THEMES_PER_BATCH} themes per batch."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_json_response(raw: str) -> list[dict]:
    """Extract a JSON array from an LLM response that may contain preamble or markdown fences."""
    text = raw.strip()
    # If there are code fences anywhere, extract content between them
    if "```" in text:
        fence_start = text.find("```")
        newline_after_fence = text.index("\n", fence_start)
        text = text[newline_after_fence + 1 :]
        fence_end = text.rfind("```")
        if fence_end != -1:
            text = text[:fence_end].rstrip()
    else:
        # Extract the JSON array by finding the outermost [ ... ]
        bracket_start = text.find("[")
        bracket_end = text.rfind("]")
        if bracket_start != -1 and bracket_end != -1:
            text = text[bracket_start : bracket_end + 1]
    return json.loads(text)


def _themes_are_similar(a: str, b: str) -> bool:
    """Check whether two theme names are similar enough to merge.

    Simple heuristic: lowercase, and check if one name is contained in the other.
    """
    la, lb = a.lower().strip(), b.lower().strip()
    return la in lb or lb in la


def _merge_batch_themes(all_batch_themes: list[list[dict]]) -> list[dict]:
    """Merge themes across batches — combine similar names, sum counts, keep longest quote."""
    merged: list[dict] = []

    for batch in all_batch_themes:
        for item in batch:
            theme_name = item.get("theme") or item.get("theme_name", "Unknown")
            count = int(item.get("count", 1))
            quote = item.get("quote", "")

            # Try to find a matching existing theme
            matched = False
            for existing in merged:
                if _themes_are_similar(existing["theme"], theme_name):
                    existing["count"] += count
                    # Keep the longest quote as the most representative
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

    # Sort descending by count
    merged.sort(key=lambda t: t["count"], reverse=True)
    return merged[:TOP_N]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def extract_themes(reviews_csv_path: Path) -> list[dict]:
    """Extract top themes from a reviews CSV using batched LLM calls.

    Parameters
    ----------
    reviews_csv_path : Path
        Path to the reviews CSV (must have ``review_text`` and ``review_id`` columns).

    Returns
    -------
    list[dict]
        Top 5 themes, each with keys: ``theme``, ``count``, ``quote``, ``review_ids``.
    """
    df = pd.read_csv(reviews_csv_path)
    df = df.sort_values("review_date", ascending=False).head(200)
    logger.info("Loaded %d reviews from %s", len(df), reviews_csv_path)

    llm = LLMClient()
    all_batch_themes: list[list[dict]] = []

    # Split into batches
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

    logger.info("Processing %d batches of up to %d reviews each", len(batches), BATCH_SIZE)

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
            themes = _parse_json_response(raw)
            # Attach review IDs from this batch to each theme
            for t in themes:
                t.setdefault("review_ids", [])
                t["review_ids"].extend(batch_review_ids[:5])  # representative IDs
            all_batch_themes.append(themes)
            logger.info("Batch %d/%d: extracted %d themes", idx + 1, len(batches), len(themes))
        except Exception as exc:
            log_from_exception(
                phase="4 — Pulse Pipeline",
                module="pillars/pillar_b_voice/themes.py",
                exc=exc,
                input_val=f"batch={idx + 1}/{len(batches)}",
                fix="Skipping batch, continuing with remaining",
            )
            logger.warning("Batch %d/%d failed, skipping: %s", idx + 1, len(batches), exc)
            continue

    if not all_batch_themes:
        logger.error("All batches failed — no themes extracted")
        return []

    merged = _merge_batch_themes(all_batch_themes)
    logger.info("Merged into %d themes", len(merged))
    return merged
