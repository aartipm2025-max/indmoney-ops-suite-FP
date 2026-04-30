import streamlit as st
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def render_tab_a():
    st.header("📚 Smart-Sync Knowledge Base")
    st.caption("Ask any factual question about SBI Mutual Fund schemes. Facts only — no investment advice.")

    # Example questions
    with st.expander("💡 Example questions", expanded=False):
        st.markdown("""
        - What is the exit load for SBI Bluechip Fund?
        - What is the expense ratio of SBI Small Cap Fund?
        - What is the minimum SIP for SBI ELSS Tax Saver Fund?
        - What is exit load and why does ELSS have no exit load?
        - Who is the fund manager of SBI Midcap Fund?
        """)

    # Query input
    query = st.text_input("Ask a question:", placeholder="e.g., What is the exit load for SBI Bluechip Fund?")

    if query:
        progress_text = st.empty()
        progress_bar = st.progress(0)

        progress_text.text("Routing query...")
        progress_bar.progress(20)

        from pillars.pillar_a_knowledge.answerer import ask

        progress_text.text("Searching knowledge base...")
        progress_bar.progress(50)

        result = ask(query)

        progress_text.empty()
        progress_bar.empty()

        if result.get("refused"):
            st.warning(f"⚠️ {result['message']}")
            if result.get("educational_link"):
                st.markdown(f"📖 [Learn more]({result['educational_link']})")

        elif result.get("error"):
            st.error(f"❌ {result['message']}")

        else:
            # Success — show answer
            st.markdown(f"**Route:** {result.get('route', 'N/A')} | **Model:** {result.get('model_name', 'N/A')}")

            st.markdown("### Answer")

            # Display bullets WITHOUT any source tags visible
            all_sources = set()
            for i, bullet in enumerate(result.get("bullets", []), 1):
                text = bullet.get("text", "")

                sources = re.findall(r'\[source:([^\]]+)\]', text)
                all_sources.update(sources)

                clean_text = re.sub(r'\s*\[source:[^\]]+\]\s*', ' ', text)
                clean_text = re.sub(r'\[doc_id=[^\]]+\]', '', clean_text)
                clean_text = clean_text.strip()

                st.markdown(f"""
                <div class="answer-bullet">
                    <div style="font-size: 1.1em; line-height: 1.6;">
                        <strong>{i}.</strong> {clean_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Show ALL unique sources ONCE at the bottom
            if all_sources:
                st.markdown("---")
                st.markdown("### 📎 Sources")

                clean_sources = []
                for s in sorted(all_sources):
                    clean_s = s.replace('doc_id=', '').strip()
                    if clean_s not in clean_sources:
                        clean_sources.append(clean_s)

                source_html = " ".join([f'<span class="source-tag">{s}</span>' for s in clean_sources])
                st.markdown(source_html, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Facts-only. No investment advice. Last updated from sources: 2026-04-23.")