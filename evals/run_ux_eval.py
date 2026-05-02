import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import pandas as pd
from pillars.pillar_b_voice.themes import extract_themes
from pillars.pillar_b_voice.trends import compute_trends
from pillars.pillar_b_voice.pulse import generate_pulse
from pillars.pillar_b_voice.voice_agent import VoiceAgent


def run_ux_eval():
    results = {}

    # Pulse
    reviews_path = Path("data/reviews/reviews.csv")
    df = pd.read_csv(reviews_path)
    themes = extract_themes(reviews_path)
    themes_with_trends = compute_trends(themes, reviews_path)
    pulse = generate_pulse(themes_with_trends, len(df), ("2026-01-01", "2026-04-30"))

    word_count = pulse.get("word_count", 999)
    action_count = len(pulse.get("actions", []))

    results["pulse_word_count"] = {
        "actual": word_count,
        "requirement": "≤250",
        "status": "pass" if word_count <= 250 else "fail"
    }

    results["pulse_action_count"] = {
        "actual": action_count,
        "requirement": "exactly 3",
        "status": "pass" if action_count == 3 else "fail"
    }

    # Voice
    top_theme = themes_with_trends[0]["theme"] if themes_with_trends else "general"
    agent = VoiceAgent(top_theme=top_theme)
    greeting = agent.process_turn("hello")
    theme_mentioned = top_theme.lower() in greeting["response"].lower()

    results["voice_theme_awareness"] = {
        "top_theme": top_theme,
        "theme_mentioned": theme_mentioned,
        "status": "pass" if theme_mentioned else "fail"
    }

    Path(__file__).parent.joinpath("ux_eval_results.json").write_text(json.dumps(results, indent=2))

    print(f"\n{'='*60}")
    print(f"UX EVAL:")
    print(f"  Pulse: {word_count} words, {action_count} actions")
    print(f"  Voice: Theme '{top_theme}' mentioned = {theme_mentioned}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    run_ux_eval()
