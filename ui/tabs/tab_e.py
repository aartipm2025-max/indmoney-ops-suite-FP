import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from datetime import datetime

def render_tab_e():
    st.header("📈 Evaluation Dashboard")
    st.caption("Automated testing suite: 35 RAG questions + 16 safety tests + UX compliance")

    # Run All Evals Button
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### Quick Actions")

    with col2:
        if st.button("🚀 Run All Evals", type="primary", use_container_width=True):
            with st.spinner("Running 51 tests... (~5-10 minutes)"):
                from scripts.run_all_evals import run_all_evals
                run_all_evals()
                st.success("✅ All evals complete!")
                st.balloons()
                st.rerun()

    # Individual Eval Buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔍 RAG Eval (35)", use_container_width=True):
            with st.spinner("Testing retrieval accuracy..."):
                from evals.run_rag_eval import run_rag_eval
                run_rag_eval()
                st.success("✅ RAG eval complete!")
                st.rerun()

    with col2:
        if st.button("🛡️ Safety Eval (16)", use_container_width=True):
            with st.spinner("Testing adversarial prompts..."):
                from evals.run_safety_eval import run_safety_eval
                run_safety_eval()
                st.success("✅ Safety eval complete!")
                st.rerun()

    with col3:
        if st.button("✨ UX Eval", use_container_width=True):
            with st.spinner("Testing pulse & voice..."):
                from evals.run_ux_eval import run_ux_eval
                run_ux_eval()
                st.success("✅ UX eval complete!")
                st.rerun()

    st.markdown("---")

    # Display Results
    rag_path = Path("evals/rag_eval_results.json")
    safety_path = Path("evals/safety_eval_results.json")
    ux_path = Path("evals/ux_eval_results.json")
    report_path = Path("evals/EVALS.md")

    if not rag_path.exists() and not safety_path.exists() and not ux_path.exists():
        st.info("💡 No eval results yet. Click **Run All Evals** to start testing.")
        return

    # Results Tabs
    results_tabs = st.tabs(["📊 Summary", "🔍 RAG Details", "🛡️ Safety Details", "✨ UX Details", "📄 Full Report"])

    # Tab 1: Summary
    with results_tabs[0]:
        st.subheader("Evaluation Summary")

        metrics_cols = st.columns(3)

        # RAG metrics
        if rag_path.exists():
            rag_results = json.loads(rag_path.read_text())
            total_rag = len(rag_results)
            passed_rag = sum(1 for r in rag_results if r["status"] == "pass")

            with metrics_cols[0]:
                st.metric(
                    "RAG Accuracy",
                    f"{passed_rag}/{total_rag}",
                    f"{passed_rag/total_rag*100:.1f}%",
                    delta_color="normal" if passed_rag/total_rag >= 0.7 else "inverse"
                )

        # Safety metrics
        if safety_path.exists():
            safety_results = json.loads(safety_path.read_text())
            total_safety = len(safety_results)
            passed_safety = sum(1 for r in safety_results if r["status"] == "pass")

            with metrics_cols[1]:
                st.metric(
                    "Safety (Must be 100%)",
                    f"{passed_safety}/{total_safety}",
                    "✅ PASS" if passed_safety == total_safety else "❌ FAIL"
                )

        # UX metrics
        if ux_path.exists():
            ux_results = json.loads(ux_path.read_text())
            ux_checks = sum(1 for v in ux_results.values() if v.get("status") == "pass")
            total_ux = len(ux_results)

            with metrics_cols[2]:
                st.metric(
                    "UX Compliance",
                    f"{ux_checks}/{total_ux}",
                    "✅ PASS" if ux_checks == total_ux else "⚠️ PARTIAL"
                )

    # Tab 2: RAG Details
    with results_tabs[1]:
        if rag_path.exists():
            rag_results = json.loads(rag_path.read_text())

            st.subheader(f"RAG Evaluation Results ({len(rag_results)} questions)")

            # Filter
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                status_filter = st.selectbox("Filter by status:", ["All", "Pass", "Fail"], key="rag_filter")
            with filter_col2:
                type_filter = st.selectbox("Filter by type:", ["All", "fact_only", "fee_only", "combined"], key="type_filter")

            # Apply filters
            filtered = rag_results
            if status_filter != "All":
                filtered = [r for r in filtered if r["status"] == status_filter.lower()]
            if type_filter != "All":
                filtered = [r for r in filtered if r.get("type") == type_filter]

            # Display table
            for r in filtered:
                status_emoji = "✅" if r["status"] == "pass" else "❌"

                with st.expander(f"{status_emoji} {r['id']} — {r['question'][:60]}..."):
                    col1, col2 = st.columns(2)
                    col1.metric("Faithfulness", f"{r['faithfulness_score']:.1f}/1.0")
                    col2.metric("Relevance", f"{r['relevance_score']:.1f}/1.0")

                    st.caption(f"**Type:** {r.get('type', 'N/A')}")
                    st.caption(f"**Status:** {r['status'].upper()}")
        else:
            st.info("No RAG results yet. Run the eval first.")

    # Tab 3: Safety Details
    with results_tabs[2]:
        if safety_path.exists():
            safety_results = json.loads(safety_path.read_text())

            st.subheader(f"Safety Evaluation Results ({len(safety_results)} adversarial prompts)")

            passed_count = sum(1 for r in safety_results if r["status"] == "pass")
            if passed_count == len(safety_results):
                st.success("✅ ALL ADVERSARIAL PROMPTS REFUSED CORRECTLY")
            else:
                st.error(f"❌ FAILED: Only {passed_count}/{len(safety_results)} refused")

            # Display table
            st.markdown("| ID | Prompt | Category | Refused? | Status |")
            st.markdown("|----|--------|----------|----------|--------|")
            for r in safety_results:
                refused_icon = "✅" if r["did_refuse"] else "❌"
                status_icon = "✅" if r["status"] == "pass" else "❌"
                st.markdown(f"| {r['id']} | {r['prompt'][:50]}... | {r['category']} | {refused_icon} | {status_icon} |")
        else:
            st.info("No safety results yet. Run the eval first.")

    # Tab 4: UX Details
    with results_tabs[3]:
        if ux_path.exists():
            ux_results = json.loads(ux_path.read_text())

            st.subheader("UX Evaluation Results")

            # Pulse checks
            st.markdown("### Weekly Pulse")
            col1, col2 = st.columns(2)

            pulse_wc = ux_results.get("pulse_word_count", {})
            with col1:
                status = "✅" if pulse_wc.get("status") == "pass" else "❌"
                st.metric(
                    f"{status} Word Count",
                    pulse_wc.get("actual", "N/A"),
                    f"Requirement: {pulse_wc.get('requirement', 'N/A')}"
                )

            pulse_ac = ux_results.get("pulse_action_count", {})
            with col2:
                status = "✅" if pulse_ac.get("status") == "pass" else "❌"
                st.metric(
                    f"{status} Action Items",
                    pulse_ac.get("actual", "N/A"),
                    f"Requirement: {pulse_ac.get('requirement', 'N/A')}"
                )

            # Voice checks
            st.markdown("### Voice Agent")
            voice = ux_results.get("voice_theme_awareness", {})
            status = "✅" if voice.get("status") == "pass" else "❌"

            st.markdown(f"**{status} Theme Awareness**")
            st.caption(f"Top theme: **{voice.get('top_theme', 'N/A')}**")
            st.caption(f"Mentioned in greeting: **{voice.get('theme_mentioned', False)}**")
        else:
            st.info("No UX results yet. Run the eval first.")

    # Tab 5: Full Report
    with results_tabs[4]:
        if report_path.exists():
            st.subheader("Complete Evaluation Report")

            report_content = report_path.read_text()
            st.markdown(report_content)

            # Download button
            st.download_button(
                "📥 Download EVALS.md",
                report_content,
                "EVALS.md",
                "text/markdown",
                use_container_width=True
            )
        else:
            st.info("No report generated yet. Run all evals first.")
