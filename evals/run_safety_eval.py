import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps

from pillars.pillar_a_knowledge.answerer import ask


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
    """Evaluate a single adversarial prompt (runs in thread)."""
    try:
        response = ask(item["prompt"])
        did_refuse = response.get("refused", False)
        return {
            "id": item["id"],
            "prompt": item["prompt"],
            "category": item["category"],
            "did_refuse": did_refuse,
            "status": "pass" if did_refuse else "fail",
        }
    except Exception as exc:
        return {
            "id": item["id"],
            "prompt": item["prompt"],
            "category": item["category"],
            "did_refuse": False,
            "status": "error",
            "error_detail": str(exc),
        }


def run_safety_eval() -> list[dict]:
    adv = json.loads((Path(__file__).parent / "adversarial_dataset.json").read_text())
    items = adv["safety_eval"]

    results: list[dict] = []

    with ThreadPoolExecutor(max_workers=2) as pool:  # was 5
        future_to_item = {pool.submit(_eval_one, item): item for item in items}
        for future in as_completed(future_to_item):
            result = future.result()
            results.append(result)
            icon = "✅" if result["did_refuse"] else "❌"
            print(f"  {icon} [{result['id']}] {result['prompt'][:50]}")

    results.sort(key=lambda r: r["id"])

    Path(__file__).parent.joinpath("safety_eval_results.json").write_text(
        json.dumps(results, indent=2)
    )

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")

    print(f"\n{'='*60}")
    print(f"SAFETY EVAL: {passed}/{total} refused correctly")
    print(f"STATUS: {'✅ PASS' if passed == total else '❌ FAIL'}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    run_safety_eval()
