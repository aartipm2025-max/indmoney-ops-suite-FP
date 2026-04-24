"""
tests/test_p2_data.py

Phase 2 — Data Seeding: offline pytest gate.
No network calls. No LLM calls.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
FACTSHEETS_DIR = ROOT / "data" / "factsheets" / "markdown"
FEES_DOC = ROOT / "data" / "fees" / "elss_exit_load.md"
REVIEWS_CSV = ROOT / "data" / "reviews" / "reviews.csv"
MANIFEST = ROOT / "data" / "manifests" / "source_manifest.json"

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
    "Edge cases",
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

_RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_RE_PHONE = re.compile(r"(\+?91[\s-]?)?[6-9]\d{9}")
_RE_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _h2_headings(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def _heading_present(actual: list[str], expected: str) -> bool:
    return any(a.lower().startswith(expected.lower()) for a in actual)


def _has_frontmatter_key(text: str, key: str) -> bool:
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


def _section_text(text: str, heading_prefix: str) -> str:
    lines = text.splitlines()
    capture = False
    out: list[str] = []
    for line in lines:
        if line.startswith("## "):
            h = line[3:].strip()
            if h.lower().startswith(heading_prefix.lower()):
                capture = True
                continue
            elif capture:
                break
        if capture:
            out.append(line)
    return "\n".join(out)


def _load_reviews() -> tuple[list[str], list[dict]]:
    rows: list[dict] = []
    with REVIEWS_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = list(reader.fieldnames or [])
        for row in reader:
            rows.append(row)
    return cols, rows


# ---------------------------------------------------------------------------
# Factsheet tests
# ---------------------------------------------------------------------------

def test_factsheets_5_files_exist():
    files = list(FACTSHEETS_DIR.glob("*.md"))
    assert len(files) == 5, f"Expected 5 .md files, found {len(files)}: {[f.name for f in files]}"


def test_factsheets_have_required_headings():
    files = list(FACTSHEETS_DIR.glob("*.md"))
    assert files, "No factsheet files found"
    for f in files:
        text = f.read_text(encoding="utf-8")
        headings = _h2_headings(text)
        for expected in FACTSHEET_HEADINGS:
            assert _heading_present(headings, expected), (
                f"{f.name}: missing H2 heading '{expected}'. Found: {headings}"
            )


def test_factsheets_have_frontmatter():
    files = list(FACTSHEETS_DIR.glob("*.md"))
    assert files, "No factsheet files found"
    for f in files:
        text = f.read_text(encoding="utf-8")
        assert _has_frontmatter_key(text, "source_url"), (
            f"{f.name}: frontmatter missing 'source_url' key"
        )


# ---------------------------------------------------------------------------
# Fee doc tests
# ---------------------------------------------------------------------------

def test_fees_doc_exists_with_structure():
    assert FEES_DOC.exists(), f"{FEES_DOC} does not exist"
    text = FEES_DOC.read_text(encoding="utf-8")
    headings = _h2_headings(text)
    for expected in FEES_HEADINGS:
        assert _heading_present(headings, expected), (
            f"elss_exit_load.md: missing H2 heading '{expected}'. Found: {headings}"
        )


def test_fees_doc_has_2plus_source_urls():
    assert FEES_DOC.exists(), f"{FEES_DOC} does not exist"
    text = FEES_DOC.read_text(encoding="utf-8")
    reg_section = _section_text(text, "Regulatory References")
    url_count = len(re.findall(r"https://", reg_section))
    assert url_count >= 2, (
        f"Regulatory References section has {url_count} https:// URL(s), expected >= 2"
    )


# ---------------------------------------------------------------------------
# Reviews tests
# ---------------------------------------------------------------------------

def test_reviews_csv_schema():
    assert REVIEWS_CSV.exists(), f"{REVIEWS_CSV} does not exist"
    cols, rows = _load_reviews()
    assert cols == REVIEWS_COLUMNS, f"Columns mismatch: {cols}"
    required = {"review_id", "user_handle", "rating", "review_text"}
    for i, row in enumerate(rows):
        for col in required:
            assert row.get(col), f"Row {i}: null/empty value in column '{col}'"


def test_reviews_all_redacted():
    _, rows = _load_reviews()
    bad = [i for i, r in enumerate(rows) if r.get("user_handle") != "[REDACTED]"]
    assert not bad, f"Rows with non-redacted user_handle at indices: {bad[:10]}"


def test_reviews_no_pii():
    _, rows = _load_reviews()
    hits: list[int] = []
    for i, r in enumerate(rows):
        t = r.get("review_text", "")
        if _RE_EMAIL.search(t) or _RE_PHONE.search(t) or _RE_PAN.search(t):
            hits.append(i)
    assert not hits, f"PII pattern found in review_text at row indices: {hits[:10]}"


def test_reviews_row_count_in_range():
    _, rows = _load_reviews()
    assert 200 <= len(rows) <= 300, f"Row count {len(rows)} outside range 200-300"


def test_reviews_week_split():
    _, rows = _load_reviews()
    weeks = {r.get("week") for r in rows}
    assert "week_a" in weeks, "No 'week_a' entries found in reviews"
    assert "week_b" in weeks, "No 'week_b' entries found in reviews"


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------

def test_manifest_has_20_entries():
    assert MANIFEST.exists(), f"{MANIFEST} does not exist"
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    assert len(entries) == 20, f"Expected 20 manifest entries, got {len(entries)}"


def test_manifest_cross_references():
    assert MANIFEST.exists(), f"{MANIFEST} does not exist"
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    search_dirs = [
        ROOT / "data" / "factsheets" / "markdown",
        ROOT / "data" / "fees",
    ]
    bad: list[str] = []
    for entry in data.get("entries", []):
        for fname in entry.get("used_in_docs", []):
            if not any((d / fname).exists() for d in search_dirs):
                bad.append(f"{fname} (from '{entry.get('title')}')")
    assert not bad, f"used_in_docs references that don't resolve: {bad}"


# ---------------------------------------------------------------------------
# No fake data
# ---------------------------------------------------------------------------

FORBIDDEN = [
    "synthetic",
    "fictional",
    "hypothetical",
    "example data",
    "sample fund",
]


def test_no_fake_data_phrases():
    hits: list[str] = []
    for md_file in ROOT.glob("data/**/*.md"):
        text = md_file.read_text(encoding="utf-8")
        rel = str(md_file.relative_to(ROOT))
        for i, line in enumerate(text.splitlines(), 1):
            for phrase in FORBIDDEN:
                if phrase.lower() in line.lower():
                    hits.append(f"{rel}:{i} [{phrase!r}]")
    assert not hits, "Forbidden phrases found:\n" + "\n".join(hits[:20])
