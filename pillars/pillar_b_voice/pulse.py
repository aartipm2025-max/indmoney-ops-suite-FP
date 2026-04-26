"""
Weekly Product Pulse generator.

Takes themes with trend data, sends them to ``llama-3.3-70b-versatile``
(primary tier), and produces a structured ≤250-word pulse report with
exactly 3 action items.
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.error_logger import log_from_exception  # noqa: E402
from core.llm_client import LLMClient  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_WORDS = 250
TOP_K = 3

SYSTEM_PROMPT = (
    "You are a product operations analyst. Generate a concise weekly product pulse "
    "for the INDmoney app based on user review analysis. Rules:\n"
    "1. Summary must be UNDER 250 words.\n"
    "2. Include EXACTLY 3 action ideas.\n"
    "3. Mention the top 3 themes with their trend direction.\n"
    "4. Include 3 real user quotes (provided below).\n"
    "5. Be factual and actionable. No marketing language.\n"
    "6. Format as a structured report with sections: Summary, Top Themes, "
    "User Voices, Action Items."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_user_message(
    themes: list[dict],
    total_reviews: int,
    date_range: tuple[str, str],
) -> str:
    """Serialise the analysis data into a user prompt for the LLM."""
    payload = {
        "total_reviews": total_reviews,
        "date_range": list(date_range),
        "themes": [],
    }
    for t in themes[:TOP_K]:
        trend = t.get("trend", {})
        arrow = {"up": "↑", "down": "↓", "flat": "→"}.get(
            trend.get("direction", "flat"), "?"
        )
        payload["themes"].append(
            {
                "theme": t["theme"],
                "count": t["count"],
                "trend": f"{arrow} {trend.get('pct_delta', 0):+.1f}%",
                "direction": trend.get("direction", "flat"),
                "quote": t.get("quote", ""),
            }
        )
    return json.dumps(payload, indent=2)


def _count_words(text: str) -> int:
    return len(text.split())


def _extract_actions(pulse_text: str) -> list[str]:
    """Heuristically extract action items from the pulse text."""
    actions: list[str] = []
    # Look for numbered action items
    pattern = re.compile(
        r"(?:Action\s*(?:Item)?\s*\d|^\s*\d+[\.\)]\s*)",
        re.IGNORECASE | re.MULTILINE,
    )
    lines = pulse_text.split("\n")
    in_action_section = False
    for line in lines:
        stripped = line.strip()
        if re.search(r"action\s*item", stripped, re.IGNORECASE):
            in_action_section = True
            continue
        if in_action_section and stripped:
            # Numbered or bulleted item
            cleaned = re.sub(r"^\s*[\d\-\*\•]+[\.\)]\s*", "", stripped)
            if cleaned and len(cleaned) > 5:
                actions.append(cleaned)
        # Stop after section ends (empty line after collecting some actions)
        if in_action_section and not stripped and actions:
            break

    return actions[:3]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_pulse(
    themes_with_trends: list[dict],
    total_reviews: int,
    date_range: tuple[str, str],
) -> dict:
    """Generate the weekly product pulse report.

    Parameters
    ----------
    themes_with_trends : list[dict]
        Themes with ``trend`` sub-dicts (output of ``compute_trends``).
    total_reviews : int
        Total number of reviews analysed.
    date_range : tuple[str, str]
        ``(start_date, end_date)`` as ISO strings.

    Returns
    -------
    dict
        Pulse result with keys: ``summary``, ``themes``, ``quotes``, ``actions``,
        ``total_reviews``, ``date_range``, ``word_count``, ``generated_at``.
        On failure: ``{"error": True, "message": "..."}``.
    """
    top_themes = themes_with_trends[:TOP_K]
    user_message = _build_user_message(top_themes, total_reviews, date_range)

    llm = LLMClient()

    # --- First attempt ---
    try:
        raw = llm.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            model="primary",
            temperature=0.3,
            max_tokens=1024,
        )
    except Exception as exc:
        log_from_exception(
            phase="4 — Pulse Pipeline",
            module="pillars/pillar_b_voice/pulse.py",
            exc=exc,
            input_val="generate_pulse first attempt",
        )
        logger.error("Pulse generation failed: %s", exc)
        return {"error": True, "message": str(exc)}

    word_count = _count_words(raw)
    logger.info("Pulse first attempt: %d words", word_count)

    # --- Retry if over word limit ---
    if word_count > MAX_WORDS:
        retry_instruction = (
            f"CRITICAL: your response was {word_count} words. "
            f"It MUST be under {MAX_WORDS} words. Shorten it significantly."
        )
        try:
            raw = llm.chat(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": retry_instruction},
                ],
                model="primary",
                temperature=0.2,
                max_tokens=1024,
            )
            word_count = _count_words(raw)
            logger.info("Pulse retry: %d words", word_count)
        except Exception as exc:
            log_from_exception(
                phase="4 — Pulse Pipeline",
                module="pillars/pillar_b_voice/pulse.py",
                exc=exc,
                input_val="generate_pulse retry attempt",
            )
            logger.warning("Pulse retry failed, using first attempt: %s", exc)

    # --- Build result ---
    actions = _extract_actions(raw)
    quotes = [t.get("quote", "") for t in top_themes]

    return {
        "summary": raw,
        "themes": [
            {
                "theme": t["theme"],
                "count": t["count"],
                "trend": t.get("trend", {}),
            }
            for t in top_themes
        ],
        "quotes": quotes,
        "actions": actions,
        "total_reviews": total_reviews,
        "date_range": list(date_range),
        "word_count": word_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
