#!/usr/bin/env python
"""
CLI — Run the full Pulse Pipeline.

    uv run python scripts/generate_pulse.py

Extracts themes from reviews, computes week-over-week trends,
and generates a structured weekly product pulse report.
"""

import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from pillars.pillar_b_voice.themes import extract_themes  # noqa: E402
from pillars.pillar_b_voice.trends import compute_trends  # noqa: E402
from pillars.pillar_b_voice.pulse import generate_pulse  # noqa: E402

# ---------------------------------------------------------------------------
# Configure logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pulse_pipeline")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REVIEWS_CSV = _PROJECT_ROOT / "data" / "reviews" / "reviews.csv"


def main() -> None:
    print("\n" + "═" * 70)
    print("  INDmoney — Weekly Product Pulse Pipeline")
    print("═" * 70 + "\n")

    # ------------------------------------------------------------------
    # Step 1: Extract themes
    # ------------------------------------------------------------------
    print("▸ Step 1/3: Extracting themes from reviews …")
    themes = extract_themes(REVIEWS_CSV)
    if not themes:
        print("✗ No themes extracted — aborting.")
        sys.exit(1)
    print(f"  ✓ {len(themes)} themes extracted\n")

    # ------------------------------------------------------------------
    # Step 2: Compute trends
    # ------------------------------------------------------------------
    print("▸ Step 2/3: Computing week-over-week trends …")
    themes_with_trends = compute_trends(themes, REVIEWS_CSV)
    print("  ✓ Trends attached\n")

    # ------------------------------------------------------------------
    # Step 3: Generate pulse
    # ------------------------------------------------------------------
    import pandas as pd

    df = pd.read_csv(REVIEWS_CSV)
    total_reviews = len(df)
    dates = pd.to_datetime(df["review_date"])
    date_range = (dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d"))

    print("▸ Step 3/3: Generating pulse report …")
    pulse = generate_pulse(themes_with_trends, total_reviews, date_range)

    if pulse.get("error"):
        print(f"✗ Pulse generation failed: {pulse['message']}")
        sys.exit(1)
    print("  ✓ Pulse generated\n")

    # ------------------------------------------------------------------
    # Output: Theme table
    # ------------------------------------------------------------------
    print("─" * 70)
    print("  THEME TABLE")
    print("─" * 70)
    print(f"{'Theme':<25} {'Count':>6}  {'Trend':>8}  Quote Preview")
    print("─" * 70)
    arrow_map = {"up": "↑", "down": "↓", "flat": "→"}
    for t in themes_with_trends:
        trend = t.get("trend", {})
        arrow = arrow_map.get(trend.get("direction", "flat"), "?")
        pct = trend.get("pct_delta", 0)
        trend_str = f"{arrow} {pct:+.0f}%"
        quote_preview = (t.get("quote", "")[:40] + "…") if len(t.get("quote", "")) > 40 else t.get("quote", "")
        print(f"{t['theme']:<25} {t['count']:>6}  {trend_str:>8}  {quote_preview}")
    print("─" * 70 + "\n")

    # ------------------------------------------------------------------
    # Output: Full pulse
    # ------------------------------------------------------------------
    print("═" * 70)
    print("  WEEKLY PRODUCT PULSE")
    print("═" * 70)
    print(pulse["summary"])
    print("═" * 70 + "\n")

    # ------------------------------------------------------------------
    # Output: Metadata
    # ------------------------------------------------------------------
    print(f"  Word count : {pulse['word_count']}")
    print(f"  Date range : {pulse['date_range'][0]} → {pulse['date_range'][1]}")
    print(f"  Generated  : {pulse['generated_at']}")
    print()

    # ------------------------------------------------------------------
    # Output: Action items
    # ------------------------------------------------------------------
    if pulse.get("actions"):
        print("  ACTION ITEMS")
        print("  " + "─" * 40)
        for i, action in enumerate(pulse["actions"], 1):
            print(f"  {i}. {action}")
        print()

    print("✓ Pipeline complete.\n")


if __name__ == "__main__":
    main()
