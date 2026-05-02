import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED


def run_all_evals():
    print("\n" + "=" * 60)
    print("RUNNING EVALUATION SUITE (51 TESTS) — parallel mode")
    print("=" * 60)

    from evals.run_rag_eval import run_rag_eval
    from evals.run_safety_eval import run_safety_eval
    from evals.run_ux_eval import run_ux_eval
    from evals.generate_report import generate_evals_report

    t0 = time.time()

    # Run all three evals concurrently — they are fully independent
    with ThreadPoolExecutor(max_workers=3) as pool:
        rag_future = pool.submit(run_rag_eval)
        safety_future = pool.submit(run_safety_eval)
        ux_future = pool.submit(run_ux_eval)

        # Block until all three finish
        wait([rag_future, safety_future, ux_future], return_when=ALL_COMPLETED)

    # Surface any exceptions
    for label, future in [("RAG", rag_future), ("Safety", safety_future), ("UX", ux_future)]:
        exc = future.exception()
        if exc:
            print(f"[ERROR] {label} eval raised: {exc}")

    elapsed = time.time() - t0
    print(f"\n[FINAL] All evals done in {elapsed:.1f}s — generating report...")
    generate_evals_report()

    print("\n✅ ALL EVALS COMPLETE")
    print(f"   Total time: {elapsed:.1f}s")
    print("\nResults:")
    print("  - evals/rag_eval_results.json")
    print("  - evals/safety_eval_results.json")
    print("  - evals/ux_eval_results.json")
    print("  - evals/EVALS.md")


if __name__ == "__main__":
    run_all_evals()
