import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps

from pillars.pillar_a_knowledge.answerer import ask
from evals.llm_judge import judge_faithfulness, judge_relevance


def retry_on_rate_limit(max_retries=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "rate" in str(e).lower() and attempt < max_retries - 1:
                        wait = 2 ** attempt
                        print(f"Rate limit hit, waiting {wait}s...")
                        time.sleep(wait)
                    else:
                        raise
            return func(*args, **kwargs)
        return wrapper
    return decorator


@retry_on_rate_limit(max_retries=3)
def _eval_one(item: dict) -> dict:
    """Evaluate a single golden question (runs in thread)."""
    try:
        response = ask(item["question"])

        if response.get("refused") or response.get("error"):
            return {
                "id": item["id"],
                "question": item["question"],
                "type": item.get("type", "unknown"),
                "status": "error",
                "faithfulness_score": 0.0,
                "relevance_score": 0.0,
            }

        bullets = response.get("bullets", [])
        answer_text = "\n".join(b.get("text", "") for b in bullets)

        all_sources: set[str] = set()
        for b in bullets:
            all_sources.update(re.findall(r'\[source:([^\]]+)\]', b.get("text", "")))

        faith = judge_faithfulness(item["question"], answer_text, list(all_sources))
        rel = judge_relevance(item["question"], answer_text, item["expected_answer_contains"])

        passed = faith["score"] >= 0.5 and rel["score"] >= 0.5
        return {
            "id": item["id"],
            "question": item["question"],
            "type": item.get("type", "unknown"),
            "faithfulness_score": faith["score"],
            "relevance_score": rel["score"],
            "status": "pass" if passed else "fail",
        }
    except Exception as exc:
        return {
            "id": item["id"],
            "question": item["question"],
            "type": item.get("type", "unknown"),
            "status": "error",
            "faithfulness_score": 0.0,
            "relevance_score": 0.0,
            "error_detail": str(exc),
        }


def run_rag_eval() -> list[dict]:
    golden = json.loads((Path(__file__).parent / "golden_dataset.json").read_text())
    items = golden["rag_eval"]

    results: list[dict] = []

    with ThreadPoolExecutor(max_workers=2) as pool:  # was 5
        future_to_item = {pool.submit(_eval_one, item): item for item in items}
        for future in as_completed(future_to_item):
            result = future.result()
            results.append(result)
            print(f"  [{result['id']}] {result['status']} "
                  f"(faith={result.get('faithfulness_score', 0):.1f} "
                  f"rel={result.get('relevance_score', 0):.1f})")

    # Sort by ID so the JSON is stable
    results.sort(key=lambda r: r["id"])

    Path(__file__).parent.joinpath("rag_eval_results.json").write_text(
        json.dumps(results, indent=2)
    )

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    avg_faith = sum(r.get("faithfulness_score", 0.0) for r in results) / total
    avg_rel = sum(r.get("relevance_score", 0.0) for r in results) / total

    print(f"\n{'='*60}")
    print(f"RAG EVAL: {passed}/{total} passed | Faith: {avg_faith:.2f} | Rel: {avg_rel:.2f}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    run_rag_eval()
