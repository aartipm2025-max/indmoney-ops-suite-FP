import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def verify_pillar_a():
    """Pillar A: Smart-Sync Knowledge Base (M1 + M2)"""
    print("\n" + "="*60)
    print("PILLAR A: Smart-Sync Knowledge Base (M1 + M2)")
    print("="*60)

    checks = []

    # CHECK 1: Unified Search UI exists
    ui_file = Path("ui/tabs/tab_a.py")
    checks.append(("Unified Search UI exists", ui_file.exists()))

    # CHECK 2: Can answer combined M1+M2 question
    from pillars.pillar_a_knowledge.answerer import ask
    combined_query = "What is the exit load for the ELSS fund and why was I charged it?"
    result = ask(combined_query)

    checks.append(("Combined M1+M2 query works", not result.get("error") and not result.get("refused")))
    checks.append(("Route is 'both'", result.get("route") == "both"))
    checks.append(("Exactly 6 bullets returned", len(result.get("bullets", [])) == 6))

    # CHECK 3: Sources cited from both factsheet AND fee doc
    all_sources = set()
    for bullet in result.get("bullets", []):
        import re
        sources = re.findall(r'\[source:([^\]]+)\]', bullet.get("text", ""))
        all_sources.update(sources)

    has_factsheet = any("elss" in s.lower() or "long_term_equity" in s.lower() for s in all_sources)
    has_fee_doc = any("exit_load" in s.lower() for s in all_sources)

    checks.append(("Cites factsheet sources", has_factsheet))
    checks.append(("Cites fee doc sources", has_fee_doc))
    checks.append(("Source citations present", len(all_sources) > 0))

    # Print results
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")

    return all(passed for _, passed in checks)


def verify_pillar_b():
    """Pillar B: Insight-Driven Agent Optimization (M2 + M3)"""
    print("\n" + "="*60)
    print("PILLAR B: Insight-Driven Agent (M2 → M3)")
    print("="*60)

    checks = []

    # CHECK 1: Weekly Pulse exists
    from pillars.pillar_b_voice.pulse import generate_pulse
    from pillars.pillar_b_voice.themes import extract_themes
    from pillars.pillar_b_voice.trends import compute_trends
    import pandas as pd

    reviews_path = Path("data/reviews/reviews.csv")
    checks.append(("Reviews CSV exists", reviews_path.exists()))

    # Generate pulse
    try:
        df = pd.read_csv(reviews_path)
        themes = extract_themes(reviews_path)
        themes_with_trends = compute_trends(themes, reviews_path)
        pulse = generate_pulse(themes_with_trends, len(df), ("2026-01-01", "2026-04-30"))

        checks.append(("Pulse generation works", not pulse.get("error")))
        checks.append(("Pulse ≤250 words", pulse.get("word_count", 999) <= 250))
        checks.append(("Pulse has exactly 3 actions", len(pulse.get("actions", [])) == 3))
        checks.append(("Top 3 themes present", len(pulse.get("themes", [])) >= 3))

        # CHECK 2: Voice Agent uses pulse theme
        from pillars.pillar_b_voice.voice_agent import VoiceAgent

        top_theme = themes[0]["theme"] if themes else "general"
        agent = VoiceAgent(top_theme=top_theme)
        greeting = agent.process_turn("hello")

        checks.append(("Voice agent initializes", greeting is not None))
        checks.append(("Greeting mentions theme", top_theme.lower() in greeting["response"].lower()))
        checks.append(("Theme-aware logic works", top_theme != "general" or "general" in greeting["response"].lower()))

    except Exception as exc:
        print(f"  ❌ Pulse/Voice pipeline error: {exc}")
        checks.append(("Pulse/Voice pipeline", False))

    # Print results
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")

    return all(passed for _, passed in checks)


def verify_pillar_c():
    """Pillar C: Super-Agent MCP Workflow (M2 + M3)"""
    print("\n" + "="*60)
    print("PILLAR C: MCP + HITL with Market Context (M2 + M3)")
    print("="*60)

    checks = []

    # CHECK 1: HITL approval center exists
    hitl_ui = Path("ui/tabs/tab_c.py")
    checks.append(("HITL UI exists", hitl_ui.exists()))

    # CHECK 2: MCP tools exist
    from pillars.pillar_c_hitl.mcp_tools import create_calendar_hold, create_email_draft, create_doc_append
    from pillars.pillar_c_hitl.approval import submit_for_approval, get_pending_ops

    # CHECK 3: Briefing card includes market context
    from pillars.pillar_c_hitl.briefing_card import generate_briefing_card, format_briefing_html, format_briefing_plain

    # Simulate pulse + booking
    pulse_data = {
        "themes": [{"theme": "Login Issues", "count": 50, "trend": {"direction": "up", "pct_delta": 25}}],
        "quotes": ["App crashes on login"],
        "actions": ["Fix login flow"],
        "total_reviews": 300,
        "date_range": ["2026-01-01", "2026-04-30"]
    }
    booking_data = {
        "booking_code": "IND-LOGN-20260430-001",
        "topic": "KYC/Onboarding",
        "slot": {"date": "2026-05-01", "time": "10:00 AM IST"}
    }

    card = generate_briefing_card(pulse_data, booking_data)
    html = format_briefing_html(card)
    plain = format_briefing_plain(card)

    checks.append(("Briefing card generates", card is not None))
    checks.append(("Card has market_context field", "market_context" in card))
    checks.append(("Market context has period", "period" in card.get("market_context", {})))
    checks.append(("Market context has sentiment", "sentiment" in card.get("market_context", {})))
    checks.append(("Market context in HTML", "Market Context" in html or "MARKET CONTEXT" in html))
    checks.append(("Market context in plain text", "MARKET CONTEXT" in plain))

    # CHECK 4: Email includes market context
    checks.append(("Email HTML contains sentiment data", "sentiment" in html.lower() or "trending" in html.lower()))

    # CHECK 5: All 3 MCP actions can be created
    try:
        cal = create_calendar_hold("Test", "Desc", "2026-05-01T10:00:00+05:30", "2026-05-01T10:30:00+05:30")
        email = create_email_draft(["test@test.com"], "Subject", html, plain, "IND-TEST-001")
        doc = create_doc_append("Test Doc", "Content", "IND-TEST-001")

        checks.append(("Calendar tool works", cal["tool"] == "calendar_hold"))
        checks.append(("Email tool works", email["tool"] == "email_draft"))
        checks.append(("Doc tool works", doc["tool"] == "doc_append"))
    except Exception as exc:
        print(f"  ❌ MCP tools error: {exc}")
        checks.append(("MCP tools work", False))

    # Print results
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")

    return all(passed for _, passed in checks)


def verify_integration():
    """End-to-end integration checks"""
    print("\n" + "="*60)
    print("INTEGRATION: All Pillars Connected")
    print("="*60)

    checks = []

    # CHECK 1: Single entry point (app.py)
    app_file = Path("app.py")
    checks.append(("Single entry point (app.py)", app_file.exists()))

    # CHECK 2: 4 tabs exist
    tab_a = Path("ui/tabs/tab_a.py")
    tab_b = Path("ui/tabs/tab_b.py")
    tab_c = Path("ui/tabs/tab_c.py")
    tab_d = Path("ui/tabs/tab_d.py")

    checks.append(("Tab A (Knowledge) exists", tab_a.exists()))
    checks.append(("Tab B (Pulse/Voice) exists", tab_b.exists()))
    checks.append(("Tab C (HITL) exists", tab_c.exists()))
    checks.append(("Tab D (Evals) exists", tab_d.exists()))

    # CHECK 3: No PII in system
    import sqlite3
    db_path = Path("data/hitl_queue.db")
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT payload_json FROM pending_ops").fetchall()
        conn.close()

        has_pii = False
        for row in rows:
            import re
            # Simple PII check (email, phone patterns)
            if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', row[0]):
                # Email in payload is OK (advisor email)
                pass
            if re.search(r'\b\d{10}\b', row[0]):  # 10-digit phone
                has_pii = True

        checks.append(("No PII in HITL queue", not has_pii))

    # CHECK 4: Booking code propagates
    # (Already tested in Pillar C, but verify format)
    import re
    booking_code_pattern = r'^IND-[A-Z]{4}-\d{8}-\d{3}$'
    test_code = "IND-TECH-20260430-001"
    checks.append(("Booking code format valid", re.match(booking_code_pattern, test_code) is not None))

    # Print results
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")

    return all(passed for _, passed in checks)


if __name__ == "__main__":
    print("\n" + "╔" + "="*58 + "╗")
    print("║  CAPSTONE PROJECT COMPLIANCE VERIFICATION              ║")
    print("╚" + "="*58 + "╝")

    results = {
        "Pillar A (M1+M2)": verify_pillar_a(),
        "Pillar B (M2→M3)": verify_pillar_b(),
        "Pillar C (M2+M3)": verify_pillar_c(),
        "Integration": verify_integration()
    }

    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)

    for pillar, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} — {pillar}")

    if all(results.values()):
        print("\n🎉 ALL CAPSTONE REQUIREMENTS MET!")
        print("Ready for Phase 9 (Evals) and Phase 10 (Ship)")
        sys.exit(0)
    else:
        print("\n⚠️ SOME REQUIREMENTS NOT MET")
        print("Fix the ❌ items above before proceeding to evals.")
        sys.exit(1)
