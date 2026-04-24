import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google_play_scraper import Sort, reviews

from core.error_logger import log_structured_error
from core.logger import log

APP_ID = "in.indwealth"
TARGET_COUNT = 3000
BATCH_SIZE = 100
OUT_PATH = Path("data/reviews/raw/indmoney_playstore_raw.json")

KEEP_FIELDS = {
    "reviewId",
    "userName",
    "content",
    "score",
    "thumbsUpCount",
    "reviewCreatedVersion",
    "at",
}


def scrape() -> list[dict]:
    collected: list[dict] = []
    continuation_token = None

    while len(collected) < TARGET_COUNT:
        try:
            result, continuation_token = reviews(
                APP_ID,
                lang="en",
                country="in",
                sort=Sort.NEWEST,
                count=BATCH_SIZE,
                continuation_token=continuation_token,
            )
        except Exception as exc:
            log_structured_error(
                phase="2",
                module="scripts.scrape_reviews",
                error_type="Integration",
                description="Google Play Scraper network/API failure",
                input_val=f"app_id={APP_ID}, collected_so_far={len(collected)}",
                expected="Successful batch response",
                actual=str(exc),
                fix="Check network connectivity and google-play-scraper library version",
            )
            log.error(f"[scrape_reviews] Network error — stopping. {exc}")
            sys.exit(1)

        batch = [{k: v for k, v in r.items() if k in KEEP_FIELDS} for r in result]

        if len(batch) < 200 and len(collected) == 0:
            log.warning(
                f"[scrape_reviews] First batch returned only {len(batch)} reviews "
                f"(expected ≥200). Continuing."
            )

        collected.extend(batch)

        if len(collected) % 100 == 0 or len(collected) >= TARGET_COUNT:
            log.info(f"[scrape_reviews] Collected {len(collected)} reviews so far.")

        if continuation_token is None:
            log.warning(
                "[scrape_reviews] No continuation token returned — no more reviews available."
            )
            break

        if len(collected) < TARGET_COUNT:
            time.sleep(1)

    return collected[:TARGET_COUNT]


def main() -> None:
    log.info(f"[scrape_reviews] Starting scrape for {APP_ID}, target={TARGET_COUNT}")

    collected = scrape()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(collected, f, ensure_ascii=False, indent=2, default=str)

    log.info(f"[scrape_reviews] Saved {len(collected)} reviews to {OUT_PATH}")

    if collected:
        dates = [r["at"] for r in collected if r.get("at")]
        dates_sorted = sorted(str(d) for d in dates)
        print(f"\nTotal reviews scraped : {len(collected)}")
        print(f"Earliest date         : {dates_sorted[0]}")
        print(f"Latest date           : {dates_sorted[-1]}")
    else:
        print("No reviews collected.")


if __name__ == "__main__":
    main()
