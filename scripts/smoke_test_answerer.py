"""
scripts/smoke_test_answerer.py

Phase 3 smoke test: end-to-end ask() for 3 representative queries.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings  # noqa: F401  validates env before any API call
from pillars.pillar_a_knowledge.answerer import ask

QUERIES = [
    ("Q1 — fact+fee", "What is the exit load for SBI Bluechip Fund?"),
    ("Q2 — advice (expect refused)", "Should I invest in SBI Small Cap Fund?"),
    (
        "Q3 — fee+context",
        "What is the exit load for the ELSS fund and why is there no exit load?",
    ),
]


def main() -> None:
    for label, query in QUERIES:
        print(f"\n{'=' * 70}")
        print(f"{label}")
        print(f"Query : {query}")
        print("-" * 70)

        result = ask(query)

        if result.get("refused"):
            print("STATUS  : REFUSED")
            print(f"Message : {result['message']}")
            print(f"Link    : {result.get('educational_link', '')}")
        elif result.get("error"):
            print("STATUS  : ERROR")
            print(f"Message : {result['message']}")
        else:
            bullets = result.get("bullets", [])
            print(f"STATUS  : OK — {len(bullets)} bullets")
            for i, b in enumerate(bullets, 1):
                text = b["text"] if isinstance(b, dict) else b.text
                print(f"  [{i}] {text[:120]}")
            print(f"Route   : {result.get('route', '')}")
            print(f"Model   : {result.get('model_name', '')}")

    print(f"\n{'=' * 70}")
    print("Smoke test complete.")


if __name__ == "__main__":
    main()
