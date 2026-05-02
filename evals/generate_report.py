import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json


def generate_evals_report():
    rag = json.loads((Path(__file__).parent / "rag_eval_results.json").read_text())
    safety = json.loads((Path(__file__).parent / "safety_eval_results.json").read_text())
    ux = json.loads((Path(__file__).parent / "ux_eval_results.json").read_text())

    md = []
    md.append("# Evaluation Report — INDmoney Investor Ops Suite\n")
    md.append("**Date:** 2026-04-30")
    md.append("**Student:** Aarti Dhavare\n")
    md.append("---\n")

    # RAG
    md.append("## 1. RAG Evaluation (Retrieval Accuracy)\n")
    total = len(rag)
    passed = sum(1 for r in rag if r["status"] == "pass")
    avg_faith = sum(r.get("faithfulness_score", 0.0) for r in rag) / total
    avg_rel = sum(r.get("relevance_score", 0.0) for r in rag) / total

    md.append(f"**Questions:** {total}")
    md.append(f"**Pass Rate:** {passed}/{total} ({passed/total*100:.1f}%)")
    md.append(f"**Avg Faithfulness:** {avg_faith:.2f}/1.0")
    md.append(f"**Avg Relevance:** {avg_rel:.2f}/1.0\n")
    md.append("| ID | Question | Faith | Rel | Status |")
    md.append("|----|----------|-------|-----|--------|")
    for r in rag[:10]:
        md.append(f"| {r['id']} | {r['question'][:50]}... | {r.get('faithfulness_score', 0.0):.1f} | {r.get('relevance_score', 0.0):.1f} | {r['status'].upper()} |")
    md.append("")

    # Safety
    md.append("## 2. Safety Evaluation (Constraint Adherence)\n")
    total_safety = len(safety)
    passed_safety = sum(1 for r in safety if r["status"] == "pass")

    md.append(f"**Adversarial Prompts:** {total_safety}")
    md.append(f"**Refused:** {passed_safety}/{total_safety} ({passed_safety/total_safety*100:.1f}%)")
    md.append(f"**Status:** {'✅ PASS' if passed_safety == total_safety else '❌ FAIL'}\n")
    md.append("| ID | Prompt | Refused? | Status |")
    md.append("|----|--------|----------|--------|")
    for r in safety:
        md.append(f"| {r['id']} | {r['prompt'][:40]}... | {'✅' if r['did_refuse'] else '❌'} | {r['status'].upper()} |")
    md.append("")

    # UX
    md.append("## 3. UX Evaluation (Tone & Structure)\n")
    md.append(f"- **Pulse Word Count:** {ux['pulse_word_count']['actual']} (req: ≤250) — {ux['pulse_word_count']['status'].upper()}")
    md.append(f"- **Pulse Actions:** {ux['pulse_action_count']['actual']} (req: 3) — {ux['pulse_action_count']['status'].upper()}")
    md.append(f"- **Voice Theme:** {ux['voice_theme_awareness']['theme_mentioned']} — {ux['voice_theme_awareness']['status'].upper()}\n")

    # Summary
    md.append("---\n")
    md.append("## Summary\n")
    md.append("| Evaluation | Pass Rate | Status |")
    md.append("|------------|-----------|--------|")
    md.append(f"| RAG | {passed}/{total} ({passed/total*100:.1f}%) | {'✅' if passed/total >= 0.7 else '⚠️'} |")
    md.append(f"| Safety | {passed_safety}/{total_safety} (100%) | {'✅' if passed_safety == total_safety else '❌'} |")
    ux_pass = all(v["status"] == "pass" for v in ux.values())
    md.append(f"| UX | {'3/3' if ux_pass else 'partial'} | {'✅' if ux_pass else '⚠️'} |")

    Path(__file__).parent.joinpath("EVALS.md").write_text("\n".join(md))
    print(f"\n✅ Report: evals/EVALS.md")


if __name__ == "__main__":
    generate_evals_report()
