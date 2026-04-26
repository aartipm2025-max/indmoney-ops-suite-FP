import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd

from pillars.pillar_b_voice.voice_agent import VoiceAgent, VoiceState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _full_booking_flow(top_theme: str = "Payment Issues") -> dict:
    """Drive a VoiceAgent all the way to BOOKED and return the final result."""
    agent = VoiceAgent(top_theme=top_theme)
    agent.process_turn("hello")        # GREETING → DISCLAIMER
    agent.process_turn("yes")          # DISCLAIMER → TOPIC_SELECT
    agent.process_turn("1")            # TOPIC_SELECT → TIME_PREFERENCE (KYC/Onboarding)
    agent.process_turn("Monday")       # TIME_PREFERENCE → SLOT_OFFER
    agent.process_turn("1")            # SLOT_OFFER → CONFIRMATION
    result = agent.process_turn("yes") # CONFIRMATION → BOOKED
    return result, agent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_voice_agent_greeting_contains_theme():
    agent = VoiceAgent(top_theme="Technical Issues")
    result = agent.process_turn("hello")
    assert "Technical Issues" in result["response"]


def test_voice_agent_refuses_advice():
    agent = VoiceAgent(top_theme="general")
    agent.process_turn("hello")   # → DISCLAIMER
    agent.process_turn("yes")     # → TOPIC_SELECT
    result = agent.process_turn("should I invest in SBI fund")
    assert "cannot provide investment advice" in result["response"].lower()
    assert result["state"] == VoiceState.TOPIC_SELECT.value


def test_voice_agent_full_booking_flow():
    result, agent = _full_booking_flow("Payment Issues")
    assert result["booking_code"].startswith("IND-")
    assert re.match(r"^IND-[A-Z]{4}-\d{8}-\d{3}$", result["booking_code"])
    assert result["state"] == "booked"


def test_voice_agent_booking_code_contains_theme():
    result, agent = _full_booking_flow(top_theme="customer support")
    assert "SUPP" in result["booking_code"]


def test_voice_agent_transcript_recorded():
    result, agent = _full_booking_flow()
    # 6 turns → 6 user entries + 6 agent entries = 12 transcript entries
    assert len(result["transcript"]) >= 10


def test_pulse_reviews_csv_exists_and_schema():
    csv_path = Path(__file__).parent.parent / "data" / "reviews" / "reviews.csv"
    assert csv_path.exists(), "reviews.csv must exist"
    df = pd.read_csv(csv_path)
    assert 200 <= len(df) <= 300, f"Expected 200-300 rows, got {len(df)}"
    required_cols = {"review_id", "review_text", "week", "review_date"}
    assert required_cols.issubset(df.columns), f"Missing columns: {required_cols - set(df.columns)}"


def test_pulse_themes_max_5():
    from pillars.pillar_b_voice.themes import extract_themes
    csv_path = Path(__file__).parent.parent / "data" / "reviews" / "reviews.csv"
    themes = extract_themes(csv_path)
    assert len(themes) <= 5, f"Expected ≤5 themes, got {len(themes)}"
