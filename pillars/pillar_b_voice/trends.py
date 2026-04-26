"""
Week-over-week trend detection for extracted themes.

Compares theme mention counts between ``week_a`` and ``week_b`` partitions of
the reviews CSV.  Pure pandas + arithmetic — no LLM calls.
"""

import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SIGNIFICANCE_PCT_THRESHOLD = 20   # |pct_delta| must be >= this
SIGNIFICANCE_MIN_COUNT = 5        # min(week_a, week_b) must be >= this


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def compute_trends(themes: list[dict], reviews_csv_path: Path) -> list[dict]:
    """Attach week-over-week trend data to each theme.

    Parameters
    ----------
    themes : list[dict]
        Output of ``extract_themes`` — each dict has at least a ``theme`` key.
    reviews_csv_path : Path
        Path to the same reviews CSV (must have ``week`` and ``review_text`` columns).

    Returns
    -------
    list[dict]
        The input list, with each dict augmented by a ``trend`` sub-dict containing:
        ``week_a_count``, ``week_b_count``, ``abs_delta``, ``pct_delta``,
        ``direction`` (``"up"`` / ``"down"`` / ``"flat"``), and ``is_significant``.
    """
    df = pd.read_csv(reviews_csv_path)
    df["review_text_lower"] = df["review_text"].astype(str).str.lower()

    week_a = df[df["week"] == "week_a"]
    week_b = df[df["week"] == "week_b"]
    logger.info(
        "Trend detection: %d week_a reviews, %d week_b reviews",
        len(week_a),
        len(week_b),
    )

    for theme_dict in themes:
        keyword = theme_dict["theme"].lower()

        wa_count = int(week_a["review_text_lower"].str.contains(keyword, na=False).sum())
        wb_count = int(week_b["review_text_lower"].str.contains(keyword, na=False).sum())

        abs_delta = wb_count - wa_count
        pct_delta = (abs_delta / wa_count * 100) if wa_count > 0 else 0.0

        if abs_delta > 0:
            direction = "up"
        elif abs_delta < 0:
            direction = "down"
        else:
            direction = "flat"

        is_significant = (
            abs(pct_delta) >= SIGNIFICANCE_PCT_THRESHOLD
            and min(wa_count, wb_count) >= SIGNIFICANCE_MIN_COUNT
        )

        theme_dict["trend"] = {
            "week_a_count": wa_count,
            "week_b_count": wb_count,
            "abs_delta": abs_delta,
            "pct_delta": round(pct_delta, 1),
            "direction": direction,
            "is_significant": is_significant,
        }

        arrow = {"up": "↑", "down": "↓", "flat": "→"}.get(direction, "?")
        logger.info(
            "  %s: %d → %d (%+d, %+.1f%%) %s%s",
            theme_dict["theme"],
            wa_count,
            wb_count,
            abs_delta,
            pct_delta,
            arrow,
            " ★" if is_significant else "",
        )

    return themes
