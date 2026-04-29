import streamlit as st
import sys
from pathlib import Path
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
        with st.spinner("Searching knowledge base..."):
            from pillars.pillar_a_knowledge.answerer import ask
            result = ask(query)

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
            for i, bullet in enumerate(result.get("bullets", []), 1):
                text = bullet.get("text", "")
                # Extract inline source tags like [source:doc_id]
                import re
                sources = re.findall(r'\[source:([^\]]+)\]', text)
                # Remove source tags from display text
                clean_text = re.sub(r'\[source:[^\]]+\]', '', text).strip()

                # Display bullet
                st.markdown(f"**{i}.** {clean_text}")

                # Show sources as inline chips
                if sources:
                    source_html = " ".join([f'<span class="source-tag">{s}</span>' for s in sources])
                    st.markdown(source_html, unsafe_allow_html=True)
                st.markdown("")  # spacing

    st.markdown("---")
    st.caption("Facts-only. No investment advice. Last updated from sources: 2026-04-23.")
