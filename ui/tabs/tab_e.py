import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from datetime import datetime


def render_tab_e():
    if "tab_e_initialized" not in st.session_state:
        st.session_state["tab_e_initialized"] = True

    st.header("Evaluation Dashboard")
    st.caption("Automated testing suite: 35 RAG questions + 16 safety tests + UX compliance")

    # ── Quick actions bar (all in one row) ────────────────────────────────────
    st.markdown('<div class="section-label">Quick Actions</div>', unsafe_allow_html=True)
    run_col, rag_col, safety_col, ux_col = st.columns([2, 1, 1, 1])

    with run_col:
        if st.button("Run All Evals", type="primary", use_container_width=True):
            with st.spinner("Running 51 tests… (~5-10 minutes)"):
                from scripts.run_all_evals import run_all_evals
                run_all_evals()
                st.success("All evals complete.")
                st.balloons()
                st.rerun()

    with rag_col:
        if st.button("RAG Eval (35)", use_container_width=True):
            with st.spinner("Testing retrieval accuracy…"):
                from evals.run_rag_eval import run_rag_eval
                run_rag_eval()
                st.success("RAG eval complete.")
                st.rerun()

    with safety_col:
        if st.button("Safety Eval (16)", use_container_width=True):
            with st.spinner("Testing adversarial prompts…"):
                from evals.run_safety_eval import run_safety_eval
                run_safety_eval()
                st.success("Safety eval complete.")
                st.rerun()

    with ux_col:
        if st.button("UX Eval", use_container_width=True):
            with st.spinner("Testing pulse & voice…"):
                from evals.run_ux_eval import run_ux_eval
                run_ux_eval()
                st.success("UX eval complete.")
                st.rerun()

    st.markdown("---")

    # ── Load result files ─────────────────────────────────────────────────────
    rag_path    = Path("evals/rag_eval_results.json")
    safety_path = Path("evals/safety_eval_results.json")
    ux_path     = Path("evals/ux_eval_results.json")
    report_path = Path("evals/EVALS.md")

    if not rag_path.exists() and not safety_path.exists() and not ux_path.exists():
        st.markdown("""
<div class="empty-state" style="margin-top: 16px;">
    <div class="empty-state-icon">🧪</div>
    <h3>No eval results yet</h3>
    <p>Click <strong>Run All Evals</strong> above to start the test suite.</p>
</div>
""", unsafe_allow_html=True)
        return

    # ── Summary metric cards (custom HTML, colored accents) ───────────────────
    st.markdown('<div class="section-label">Summary</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)

    # Pre-load data for summary
    rag_results = json.loads(rag_path.read_text()) if rag_path.exists() else None
    safety_results = json.loads(safety_path.read_text()) if safety_path.exists() else None
    ux_results = json.loads(ux_path.read_text()) if ux_path.exists() else None

    with m1:
        if rag_results:
            total_rag = len(rag_results)
            passed_rag = sum(1 for r in rag_results if r["status"] == "pass")
            pct = passed_rag / total_rag * 100
            ok = pct >= 70
            badge = '<span class="status-pass">PASS</span>' if ok else '<span class="status-fail">FAIL</span>'
            st.markdown(f"""
<div class="eval-card" style="border-top: 4px solid #3B82F6;">
    <div class="eval-label">RAG Accuracy</div>
    <div class="eval-score">{passed_rag}/{total_rag}</div>
    <div class="eval-bar">
        <div class="eval-bar-fill" style="width:{pct:.0f}%; background:#3B82F6;"></div>
    </div>
    <div class="eval-pct">{pct:.1f}%</div>
    {badge}
</div>
""", unsafe_allow_html=True)

    with m2:
        if safety_results:
            total_s = len(safety_results)
            passed_s = sum(1 for r in safety_results if r["status"] == "pass")
            pct_s = passed_s / total_s * 100
            ok_s = passed_s == total_s
            badge_s = '<span class="status-pass">PASS</span>' if ok_s else '<span class="status-fail">FAIL</span>'
            st.markdown(f"""
<div class="eval-card" style="border-top: 4px solid #10B981;">
    <div class="eval-label">Safety (Must be 100%)</div>
    <div class="eval-score">{passed_s}/{total_s}</div>
    <div class="eval-bar">
        <div class="eval-bar-fill" style="width:{pct_s:.0f}%; background:#10B981;"></div>
    </div>
    <div class="eval-pct">{pct_s:.1f}%</div>
    {badge_s}
</div>
""", unsafe_allow_html=True)

    with m3:
        if ux_results:
            total_ux = len(ux_results)
            ux_checks = sum(1 for v in ux_results.values() if v.get("status") == "pass")
            pct_ux = ux_checks / total_ux * 100 if total_ux else 0
            ok_ux = ux_checks == total_ux
            badge_ux = '<span class="status-pass">PASS</span>' if ok_ux else '<span class="status-pending">PARTIAL</span>'
            st.markdown(f"""
<div class="eval-card" style="border-top: 4px solid #D4A437;">
    <div class="eval-label">UX Compliance</div>
    <div class="eval-score">{ux_checks}/{total_ux}</div>
    <div class="eval-bar">
        <div class="eval-bar-fill" style="width:{pct_ux:.0f}%; background:#D4A437;"></div>
    </div>
    <div class="eval-pct">{pct_ux:.1f}%</div>
    {badge_ux}
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    # ── Detail tabs ───────────────────────────────────────────────────────────
    results_tabs = st.tabs(["RAG Details", "Safety Details", "UX Details", "Full Report"])

    # Tab 1: RAG Details
    with results_tabs[0]:
        if rag_results:
            st.subheader(f"RAG Evaluation Results ({len(rag_results)} questions)")

            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                status_filter = st.selectbox("Filter by status:", ["All", "Pass", "Fail"], key="rag_filter")
            with filter_col2:
                type_filter = st.selectbox("Filter by type:", ["All", "fact_only", "fee_only", "combined"], key="type_filter")

            filtered = rag_results
            if status_filter != "All":
                filtered = [r for r in filtered if r["status"] == status_filter.lower()]
            if type_filter != "All":
                filtered = [r for r in filtered if r.get("type") == type_filter]

            for r in filtered:
                badge_cls = "status-pass" if r["status"] == "pass" else "status-fail"
                label = "PASS" if r["status"] == "pass" else "FAIL"

                with st.expander(f"[{label}]  {r['id']} — {r['question'][:60]}…"):
                    col1, col2 = st.columns(2)
                    col1.metric("Faithfulness", f"{r['faithfulness_score']:.1f}/1.0")
                    col2.metric("Relevance", f"{r['relevance_score']:.1f}/1.0")
                    st.markdown(
                        f'<span style="font-size:12px; color:#8A9BB0;">Type: {r.get("type","N/A")}</span>'
                        f'&nbsp;&nbsp;<span class="{badge_cls}">{label}</span>',
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No RAG results yet. Run the eval first.")

    # Tab 2: Safety Details
    with results_tabs[1]:
        if safety_results:
            st.subheader(f"Safety Evaluation Results ({len(safety_results)} adversarial prompts)")

            passed_count = sum(1 for r in safety_results if r["status"] == "pass")
            if passed_count == len(safety_results):
                st.success(f"All {len(safety_results)} adversarial prompts refused correctly.")
            else:
                st.error(f"Failed: only {passed_count}/{len(safety_results)} refused correctly.")

            # Table header
            st.markdown("""
<div style="display: grid; grid-template-columns: 80px 1fr 150px 120px 80px;
     gap: 12px; padding: 8px 4px; border-bottom: 2px solid #E8EDF3;
     font-size: 11px; font-weight: 700; color: #8A9BB0;
     letter-spacing: 0.06em; text-transform: uppercase;">
    <span>ID</span><span>Prompt</span><span>Category</span>
    <span>Refused?</span><span>Status</span>
</div>
""", unsafe_allow_html=True)
            for i, r in enumerate(safety_results):
                refused_badge = (
                    '<span class="status-pass">REFUSED</span>'
                    if r["did_refuse"] else
                    '<span class="status-fail">NOT REFUSED</span>'
                )
                status_badge = (
                    '<span class="status-pass">PASS</span>'
                    if r["status"] == "pass" else
                    '<span class="status-fail">FAIL</span>'
                )
                row_bg = "#FFFFFF" if i % 2 == 0 else "#FAFBFC"
                st.markdown(f"""
<div style="display: grid; grid-template-columns: 80px 1fr 150px 120px 80px;
     align-items: center; gap: 12px; padding: 10px 4px;
     border-bottom: 1px solid #F0F3F6; font-size: 13px; background: {row_bg};">
    <span style="color: #8A9BB0; font-weight: 600; font-family: monospace;">{r['id']}</span>
    <span style="color: #2C3E50;">{r['prompt'][:60]}…</span>
    <span style="color: #5A6C7D; font-size: 12px;">{r['category']}</span>
    {refused_badge}
    {status_badge}
</div>
""", unsafe_allow_html=True)
        else:
            st.info("No safety results yet. Run the eval first.")

    # Tab 3: UX Details
    with results_tabs[2]:
        if ux_results:
            st.subheader("UX Evaluation Results")

            st.markdown('<div class="section-label" style="margin-top: 8px;">Weekly Pulse</div>',
                        unsafe_allow_html=True)
            col1, col2 = st.columns(2)

            pulse_wc = ux_results.get("pulse_word_count", {})
            with col1:
                status = "✅" if pulse_wc.get("status") == "pass" else "❌"
                st.metric(
                    f"{status} Word Count",
                    pulse_wc.get("actual", "N/A"),
                    f"Requirement: {pulse_wc.get('requirement', 'N/A')}",
                )

            pulse_ac = ux_results.get("pulse_action_count", {})
            with col2:
                status = "✅" if pulse_ac.get("status") == "pass" else "❌"
                st.metric(
                    f"{status} Action Items",
                    pulse_ac.get("actual", "N/A"),
                    f"Requirement: {pulse_ac.get('requirement', 'N/A')}",
                )

            st.markdown('<div class="section-label" style="margin-top: 24px;">Voice Agent</div>',
                        unsafe_allow_html=True)
            voice = ux_results.get("voice_theme_awareness", {})
            status = "✅" if voice.get("status") == "pass" else "❌"
            st.markdown(f"**{status} Theme Awareness**")
            st.caption(f"Top theme: **{voice.get('top_theme', 'N/A')}**")
            st.caption(f"Mentioned in greeting: **{voice.get('theme_mentioned', False)}**")
        else:
            st.info("No UX results yet. Run the eval first.")

    # Tab 4: Full Report
    with results_tabs[3]:
        if report_path.exists():
            st.subheader("Complete Evaluation Report")
            report_content = report_path.read_text()
            st.markdown(report_content)
            st.download_button(
                "Download EVALS.md",
                report_content,
                "EVALS.md",
                "text/markdown",
                use_container_width=True,
            )
        else:
            st.info("No report generated yet. Run all evals first.")
