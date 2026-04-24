"""
scripts/generate_source_manifest.py

Phase 2 Sub-step 6: Build source manifest for all URLs used in data/.
Outputs: data/manifests/source_manifest.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from core.logger import log

ROOT = Path(__file__).parent.parent
OUT_PATH = ROOT / "data" / "manifests" / "source_manifest.json"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Hardcoded URL entries — exactly 20
# ---------------------------------------------------------------------------
_ENTRIES = [
    {
        "url": "https://www.sbimf.com/sbimf-scheme-details/sbi-large-cap-fund-(formerly-known-as-sbi-bluechip-fund)-43",
        "title": "SBI Large Cap Fund",
        "category": "factsheet",
        "used_in_docs": ["sbi_bluechip.md"],
    },
    {
        "url": "https://www.sbimf.com/sbimf-scheme-details/sbi-small-cap-fund-329",
        "title": "SBI Small Cap Fund",
        "category": "factsheet",
        "used_in_docs": ["sbi_small_cap.md"],
    },
    {
        "url": "https://www.sbimf.com/sbimf-scheme-details/sbi-equity-hybrid-fund-5",
        "title": "SBI Equity Hybrid Fund",
        "category": "factsheet",
        "used_in_docs": ["sbi_equity_hybrid.md"],
    },
    {
        "url": "https://www.sbimf.com/sbimf-scheme-details/sbi-midcap-fund-34",
        "title": "SBI Midcap Fund",
        "category": "factsheet",
        "used_in_docs": ["sbi_midcap.md"],
    },
    {
        "url": "https://www.sbimf.com/sbimf-scheme-details/sbi-elss-tax-saver-fund-(formerly-known-as-sbi-long-term-equity-fund)-3",
        "title": "SBI ELSS Tax Saver Fund",
        "category": "factsheet",
        "used_in_docs": ["sbi_long_term_equity.md", "elss_exit_load.md"],
    },
    {
        "url": "https://investor.sebi.gov.in/knowledge-centre/exit-load.html",
        "title": "SEBI — Exit Load",
        "category": "regulatory",
        "used_in_docs": ["elss_exit_load.md"],
    },
    {
        "url": "https://www.sebi.gov.in/legal/regulations/sep-2019/securities-and-exchange-board-of-india-mutual-funds-regulations-1996-last-amended-on-september-23-2019-_41350.html",
        "title": "SEBI MF Regulations 1996",
        "category": "regulatory",
        "used_in_docs": [],
    },
    {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/1337083696184.pdf",
        "title": "SEBI Riskometer Circular",
        "category": "regulatory",
        "used_in_docs": [],
    },
    {
        "url": "https://www.amfiindia.com/investor/investor-awareness-program",
        "title": "AMFI Investor Awareness",
        "category": "reference",
        "used_in_docs": [],
    },
    {
        "url": "https://www.amfiindia.com/investor/knowledge-center-info?zoneName=IntroductionMutualFunds",
        "title": "AMFI — MF Basics",
        "category": "reference",
        "used_in_docs": [],
    },
    {
        "url": "https://www.amfiindia.com/investor/become-mf-distributor?zoneName=sip",
        "title": "AMFI — SIP",
        "category": "reference",
        "used_in_docs": [],
    },
    {
        "url": "https://www.amfiindia.com/kyc",
        "title": "AMFI — KYC",
        "category": "reference",
        "used_in_docs": [],
    },
    {
        "url": "https://www.sbimf.com",
        "title": "SBI MF Homepage",
        "category": "reference",
        "used_in_docs": [],
    },
    {
        "url": "https://www.sbimf.com/faq",
        "title": "SBI MF FAQ",
        "category": "reference",
        "used_in_docs": [],
    },
    {
        "url": "https://www.sbimf.com/offer-document-sid-kim",
        "title": "SBI MF — SID/KIM",
        "category": "reference",
        "used_in_docs": [],
    },
    {
        "url": "https://play.google.com/store/apps/details?id=in.indwealth",
        "title": "INDmoney Play Store",
        "category": "app_listing",
        "used_in_docs": [],
    },
    {
        "url": "https://www.incometaxindia.gov.in/section-80-c",
        "title": "Income Tax — Section 80C",
        "category": "regulatory",
        "used_in_docs": ["elss_exit_load.md"],
    },
    {
        "url": "https://www.incometaxindia.gov.in/sale-of-shares",
        "title": "Income Tax — Capital Gains",
        "category": "regulatory",
        "used_in_docs": [],
    },
    {
        "url": "https://www.camsonline.com/Investors",
        "title": "CAMS Investor Services",
        "category": "reference",
        "used_in_docs": [],
    },
    {
        "url": "https://www.indmoney.com/help/mutual-funds/what-is-exit-load",
        "title": "INDmoney Help — Exit Load",
        "category": "reference",
        "used_in_docs": ["elss_exit_load.md"],
    },
]

_OK_CODES = {200, 201, 301, 302, 308}
_HEADERS = {"User-Agent": "INDmoneyOpsSuite/1.0"}


def _verify(client: httpx.Client, entry: dict) -> dict:
    url = entry["url"]
    now = datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        resp = client.get(url, timeout=15, follow_redirects=True)
        code = resp.status_code
        status = "ok" if code in _OK_CODES else f"http_{code}"
    except httpx.TimeoutException:
        status = "error_timeout"
    except httpx.RequestError as exc:
        reason = type(exc).__name__.lower()
        status = f"error_{reason}"

    log.info("  [{}] {} — {}", status, entry["title"], url)
    return {
        "url": url,
        "title": entry["title"],
        "category": entry["category"],
        "used_in_docs": entry["used_in_docs"],
        "last_verified": now,
        "status": status,
    }


def main() -> None:
    log.info("generate_source_manifest: verifying {} URLs", len(_ENTRIES))

    verified: list[dict] = []
    with httpx.Client(headers=_HEADERS) as client:
        for i, entry in enumerate(_ENTRIES, 1):
            log.info("({}/{}) checking: {}", i, len(_ENTRIES), entry["url"])
            result = _verify(client, entry)
            verified.append(result)

    generated_at = datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    ok_count = sum(1 for e in verified if e["status"] == "ok")
    broken_count = len(verified) - ok_count

    manifest = {
        "generated_at": generated_at,
        "total_urls": len(verified),
        "verified_ok": ok_count,
        "broken": broken_count,
        "entries": verified,
    }

    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    log.info("Manifest written to {}", OUT_PATH)

    # Summary
    print("\n" + "=" * 60)
    print("  SOURCE MANIFEST SUMMARY")
    print("=" * 60)
    print(f"  Total URLs   : {len(verified)}")
    print(f"  Verified OK  : {ok_count}")
    print(f"  Broken       : {broken_count}")

    broken = [e for e in verified if e["status"] != "ok"]
    if broken:
        print("\n  Broken URLs:")
        for e in broken:
            print(f"    [{e['status']}] {e['title']}")
            print(f"           {e['url']}")
    else:
        print("\n  All URLs returned an acceptable status.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
