"""
scripts/validate_data.py

Phase 2 — Data Seeding: validation gate.
Exit 0 = all checks pass. Exit 1 = one or more checks fail.
"""

from __future__ import annotations

import contextlib
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.error_logger import log_structured_error

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
FACTSHEETS_DIR = ROOT / "data" / "factsheets" / "markdown"
FEES_DOC = ROOT / "data" / "fees" / "elss_exit_load.md"
REVIEWS_CSV = ROOT / "data" / "reviews" / "reviews.csv"
MANIFEST = ROOT / "data" / "manifests" / "source_manifest.json"

# ---------------------------------------------------------------------------
# Expected structure
# ---------------------------------------------------------------------------
FACTSHEET_HEADINGS = [
    "Fund Overview",
    "Key Facts",
    "Expense Ratio",
    "Exit Load",
    "Minimum Investment",
    "Top Holdings",
    "Taxation",
]

FEES_HEADINGS = [
    "What it is",
    "Who's involved",
    "How it's calculated",
    "Worked Example",
    "Edge cases",          # prefix — actual heading may have more words
    "Regulatory References",
]

REVIEWS_COLUMNS = [
    "review_id",
    "user_handle",
    "rating",
    "theme",
    "week",
    "review_date",
    "review_text",
    "app_version",
    "platform",
]

FORBIDDEN_WORDS = [
    "synthetic",
    "fictional",
    "hypothetical",
    "example data",
    "sample fund",
]

_RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_RE_PHONE = re.compile(r"(\+?91[\s-]?)?[6-9]\d{9}")
_RE_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")

PASS = "✅"
FAIL = "❌"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_fail(check: str, detail: str) -> None:
    log_structured_error(
        phase="2 — Data Seeding",
        module="scripts.validate_data",
        error_type="Validation",
        description=check,
        input_val="",
        expected="Check passes",
        actual=detail,
        fix="Remediate the data file(s) listed above",
        status="Pending",
    )


def _extract_h2_headings(text: str) -> list[str]:
    """Return the text after '## ' for every H2 line."""
    return [
        line[3:].strip()
        for line in text.splitlines()
        if line.startswith("## ")
    ]


def _has_frontmatter_key(text: str, key: str) -> bool:
    """True if the YAML frontmatter block contains a line starting with key."""
    in_fm = False
    for i, line in enumerate(text.splitlines()):
        if i == 0 and line.strip() == "---":
            in_fm = True
            continue
        if in_fm:
            if line.strip() == "---":
                break
            if line.strip().startswith(key):
                return True
    return False


def _headings_match(actual: list[str], expected: list[str]) -> list[str]:
    """Return list of expected headings not found in actual (prefix-insensitive)."""
    missing = []
    for exp in expected:
        found = any(a.lower().startswith(exp.lower()) for a in actual)
        if not found:
            missing.append(exp)
    return missing


def _section_text(text: str, heading: str) -> str:
    """Return text between a heading (prefix-matched) and the next ## heading."""
    lines = text.splitlines()
    capture = False
    out: list[str] = []
    for line in lines:
        if line.startswith("## "):
            h = line[3:].strip()
            if h.lower().startswith(heading.lower()):
                capture = True
                continue
            elif capture:
                break
        if capture:
            out.append(line)
    return "\n".join(out)


def _count_https_urls(text: str) -> int:
    return len(re.findall(r"https://", text))


def _parse_iso(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_factsheets() -> bool:
    ok = True
    files = sorted(FACTSHEETS_DIR.glob("*.md"))

    # 5 files
    if len(files) == 5:
        print(f"{PASS} Factsheets: exactly 5 .md files found")
    else:
        msg = f"found {len(files)}, expected 5"
        print(f"{FAIL} Factsheets: file count — {msg}")
        _log_fail("Factsheet file count", msg)
        ok = False

    for f in files:
        text = f.read_text(encoding="utf-8")
        name = f.name

        # H2 headings
        headings = _extract_h2_headings(text)
        missing = _headings_match(headings, FACTSHEET_HEADINGS)
        if not missing:
            print(f"{PASS} Factsheets [{name}]: all 7 H2 headings present")
        else:
            msg = f"missing: {missing}"
            print(f"{FAIL} Factsheets [{name}]: headings — {msg}")
            _log_fail(f"Factsheet headings [{name}]", msg)
            ok = False

        # frontmatter source_url
        if _has_frontmatter_key(text, "source_url"):
            print(f"{PASS} Factsheets [{name}]: frontmatter has source_url")
        else:
            msg = "no source_url key in frontmatter"
            print(f"{FAIL} Factsheets [{name}]: frontmatter — {msg}")
            _log_fail(f"Factsheet frontmatter [{name}]", msg)
            ok = False

        # word count >= 200
        wc = len(text.split())
        if wc >= 200:
            print(f"{PASS} Factsheets [{name}]: word count {wc} >= 200")
        else:
            msg = f"word count {wc} < 200"
            print(f"{FAIL} Factsheets [{name}]: word count — {msg}")
            _log_fail(f"Factsheet word count [{name}]", msg)
            ok = False

    return ok


def check_fees() -> bool:
    ok = True

    if not FEES_DOC.exists():
        msg = f"{FEES_DOC} not found"
        print(f"{FAIL} Fees: {msg}")
        _log_fail("Fee doc existence", msg)
        return False

    text = FEES_DOC.read_text(encoding="utf-8")

    # H2 headings
    headings = _extract_h2_headings(text)
    missing = _headings_match(headings, FEES_HEADINGS)
    if not missing:
        print(f"{PASS} Fees: all 6 H2 headings present")
    else:
        msg = f"missing: {missing}"
        print(f"{FAIL} Fees: headings — {msg}")
        _log_fail("Fee doc headings", msg)
        ok = False

    # >= 2 https:// URLs in Regulatory References section
    reg_section = _section_text(text, "Regulatory References")
    url_count = _count_https_urls(reg_section)
    if url_count >= 2:
        print(f"{PASS} Fees: Regulatory References has {url_count} URLs (>= 2)")
    else:
        msg = f"only {url_count} https:// URL(s) in Regulatory References section"
        print(f"{FAIL} Fees: regulatory URLs — {msg}")
        _log_fail("Fee doc regulatory URL count", msg)
        ok = False

    # word count 300-900
    wc = len(text.split())
    if 300 <= wc <= 900:
        print(f"{PASS} Fees: word count {wc} in range 300-900")
    else:
        msg = f"word count {wc} outside 300-900"
        print(f"{FAIL} Fees: word count — {msg}")
        _log_fail("Fee doc word count", msg)
        ok = False

    return ok


def check_reviews() -> bool:
    ok = True

    if not REVIEWS_CSV.exists():
        msg = f"{REVIEWS_CSV} not found"
        print(f"{FAIL} Reviews: {msg}")
        _log_fail("Reviews CSV existence", msg)
        return False

    rows: list[dict] = []
    with REVIEWS_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        actual_cols = list(reader.fieldnames or [])
        for row in reader:
            rows.append(row)

    n = len(rows)

    # 9 columns in exact order
    if actual_cols == REVIEWS_COLUMNS:
        print(f"{PASS} Reviews: 9 columns in correct order")
    else:
        msg = f"columns: {actual_cols}"
        print(f"{FAIL} Reviews: columns — {msg}")
        _log_fail("Reviews CSV columns", msg)
        ok = False

    # 200-300 rows
    if 200 <= n <= 300:
        print(f"{PASS} Reviews: {n} rows (200-300)")
    else:
        msg = f"{n} rows, expected 200-300"
        print(f"{FAIL} Reviews: row count — {msg}")
        _log_fail("Reviews CSV row count", msg)
        ok = False

    # all user_handle == "[REDACTED]"
    bad_handles = [r for r in rows if r.get("user_handle") != "[REDACTED]"]
    if not bad_handles:
        print(f"{PASS} Reviews: all user_handle == \"[REDACTED]\"")
    else:
        msg = f"{len(bad_handles)} rows with non-redacted user_handle"
        print(f"{FAIL} Reviews: user_handle — {msg}")
        _log_fail("Reviews user_handle PII", msg)
        ok = False

    # zero PII in review_text
    pii_hits = 0
    for r in rows:
        t = r.get("review_text", "")
        if _RE_EMAIL.search(t) or _RE_PHONE.search(t) or _RE_PAN.search(t):
            pii_hits += 1
    if pii_hits == 0:
        print(f"{PASS} Reviews: zero PII matches in review_text")
    else:
        msg = f"{pii_hits} rows still contain PII patterns"
        print(f"{FAIL} Reviews: PII in review_text — {msg}")
        _log_fail("Reviews PII leakage", msg)
        ok = False

    # date span >= 6 weeks
    dates: list[datetime] = []
    for r in rows:
        with contextlib.suppress(Exception):
            dates.append(_parse_iso(r["review_date"]))
    if dates:
        span_days = (max(dates) - min(dates)).days
        span_weeks = span_days / 7
        if span_weeks >= 6:
            print(f"{PASS} Reviews: date span {span_weeks:.1f} weeks (>= 6)")
        else:
            msg = f"span {span_weeks:.1f} weeks < 6"
            print(f"{FAIL} Reviews: date span — {msg}")
            _log_fail("Reviews date span", msg)
            ok = False
    else:
        msg = "no valid review_date values parsed"
        print(f"{FAIL} Reviews: date span — {msg}")
        _log_fail("Reviews date parse", msg)
        ok = False

    # both week_a and week_b non-empty
    weeks = {r.get("week") for r in rows}
    if "week_a" in weeks and "week_b" in weeks:
        print(f"{PASS} Reviews: both week_a and week_b present")
    else:
        msg = f"week values found: {weeks}"
        print(f"{FAIL} Reviews: week split — {msg}")
        _log_fail("Reviews week split", msg)
        ok = False

    return ok


def check_manifest() -> bool:
    ok = True

    if not MANIFEST.exists():
        msg = f"{MANIFEST} not found"
        print(f"{FAIL} Manifest: {msg}")
        _log_fail("Manifest existence", msg)
        return False

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = data.get("entries", [])

    # 20 entries
    if len(entries) == 20:
        print(f"{PASS} Manifest: exactly 20 entries")
    else:
        msg = f"found {len(entries)}, expected 20"
        print(f"{FAIL} Manifest: entry count — {msg}")
        _log_fail("Manifest entry count", msg)
        ok = False

    # >= 16 with status "ok"
    ok_count = sum(1 for e in entries if e.get("status") == "ok")
    if ok_count >= 16:
        print(f"{PASS} Manifest: {ok_count}/20 entries have status 'ok' (>= 16)")
    else:
        msg = f"only {ok_count}/20 entries have status 'ok'"
        print(f"{FAIL} Manifest: ok count — {msg}")
        _log_fail("Manifest ok count", msg)
        ok = False

    # used_in_docs cross-reference
    search_dirs = [
        ROOT / "data" / "factsheets" / "markdown",
        ROOT / "data" / "fees",
    ]
    bad_refs: list[str] = []
    for entry in entries:
        for fname in entry.get("used_in_docs", []):
            found = any((d / fname).exists() for d in search_dirs)
            if not found:
                bad_refs.append(f"{fname} (from {entry.get('title')})")
    if not bad_refs:
        print(f"{PASS} Manifest: all used_in_docs references resolve to real files")
    else:
        msg = f"unresolved: {bad_refs}"
        print(f"{FAIL} Manifest: used_in_docs — {msg}")
        _log_fail("Manifest used_in_docs cross-reference", msg)
        ok = False

    return ok


def check_pii_sweep() -> bool:
    ok = True
    hits: list[str] = []

    for md_file in ROOT.glob("data/**/*.md"):
        text = md_file.read_text(encoding="utf-8")
        rel = md_file.relative_to(ROOT)
        for i, line in enumerate(text.splitlines(), 1):
            if _RE_EMAIL.search(line) or _RE_PAN.search(line):
                hits.append(f"{rel}:{i}: {line.strip()[:80]}")
            # Phone pattern only on non-URL lines to avoid false positives
            stripped = re.sub(r"https?://\S+", "", line)
            if _RE_PHONE.search(stripped):
                hits.append(f"{rel}:{i} [phone]: {line.strip()[:80]}")

    if not hits:
        print(f"{PASS} PII sweep: zero matches across all .md files in data/")
    else:
        msg = f"{len(hits)} PII match(es) found"
        print(f"{FAIL} PII sweep: {msg}")
        for h in hits[:10]:
            print(f"  {h}")
        _log_fail("PII sweep", msg)
        ok = False

    return ok


def check_no_fake_data() -> bool:
    ok = True
    hits: list[str] = []

    for md_file in ROOT.glob("data/**/*.md"):
        text = md_file.read_text(encoding="utf-8")
        rel = md_file.relative_to(ROOT)
        for i, line in enumerate(text.splitlines(), 1):
            for word in FORBIDDEN_WORDS:
                if word.lower() in line.lower():
                    hits.append(f"{rel}:{i} [{word!r}]: {line.strip()[:80]}")

    if not hits:
        print(f"{PASS} No-fake-data: zero forbidden phrases across all .md files in data/")
    else:
        msg = f"{len(hits)} forbidden phrase(s) found"
        print(f"{FAIL} No-fake-data: {msg}")
        for h in hits[:10]:
            print(f"  {h}")
        _log_fail("Fake data phrases", msg)
        ok = False

    return ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 60)
    print("  PHASE 2 DATA VALIDATION GATE")
    print("=" * 60 + "\n")

    results = [
        ("Factsheets", check_factsheets()),
        ("Fees",       check_fees()),
        ("Reviews",    check_reviews()),
        ("Manifest",   check_manifest()),
        ("PII sweep",  check_pii_sweep()),
        ("No fake data", check_no_fake_data()),
    ]

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
        icon = PASS if passed else FAIL
        print(f"  {icon}  {name}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("  ✅ ALL CHECKS PASSED — exit 0")
    else:
        print("  ❌ ONE OR MORE CHECKS FAILED — exit 1")
    print("=" * 60 + "\n")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
