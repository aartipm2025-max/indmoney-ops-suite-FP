import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import re
import time

from pillars.pillar_a_knowledge.answerer import ask
from evals.llm_judge import judge_faithfulness, judge_relevance


def run_rag_eval():
    golden = json.loads((Path(__file__).parent / "golden_dataset.json").read_text())

    results = []

    for idx, item in enumerate(golden["rag_eval"]):
        print(f"[{item['id']}] {item['question'][:60]}...")

        try:
            response = ask(item["question"])

            if response.get("refused") or response.get("error"):
                results.append({
                    "id": item["id"],
                    "question": item["question"],
                    "type": item.get("type", "unknown"),
                    "status": "error",
                    "faithfulness_score": 0.0,
                    "relevance_score": 0.0,
                })
                continue

            bullets = response.get("bullets", [])
            answer_text = "\n".join(b.get("text", "") for b in bullets)

            all_sources: set[str] = set()
            for b in bullets:
                all_sources.update(re.findall(r'\[source:([^\]]+)\]', b.get("text", "")))

            time.sleep(2)
            faith = judge_faithfulness(item["question"], answer_text, list(all_sources))
            time.sleep(2)
            rel = judge_relevance(item["question"], answer_text, item["expected_answer_contains"])

            passed = faith["score"] >= 0.5 and rel["score"] >= 0.5
            results.append({
                "id": item["id"],
                "question": item["question"],
                "type": item.get("type", "unknown"),
                "faithfulness_score": faith["score"],
                "relevance_score": rel["score"],
                "status": "pass" if passed else "fail",
            })

        except Exception as e:
            print(f"Error on {item['id']}: {e}")
            results.append({
                "id": item["id"],
                "question": item["question"],
                "type": item.get("type", "unknown"),
                "status": "error",
                "faithfulness_score": 0.0,
                "relevance_score": 0.0,
            })

        if idx < len(golden["rag_eval"]) - 1:
            time.sleep(3)

    Path(__file__).parent.joinpath("rag_eval_results.json").write_text(
        json.dumps(results, indent=2)
    )

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    avg_faith = sum(r.get("faithfulness_score", 0.0) for r in results) / total if total else 0
    avg_rel = sum(r.get("relevance_score", 0.0) for r in results) / total if total else 0

    print(f"\n{'='*60}")
    print(f"RAG EVAL: {passed}/{total} passed | Faith: {avg_faith:.2f} | Rel: {avg_rel:.2f}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    run_rag_eval()
