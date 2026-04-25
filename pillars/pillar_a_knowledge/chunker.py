"""
pillars/pillar_a_knowledge/chunker.py

Markdown-header-aware chunker for the SBI MF knowledge base.
No external dependencies — uses pathlib and re only.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter_dict, body_text). Body starts after closing ---."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    fm_lines: list[str] = []
    end_idx: int | None = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break
        fm_lines.append(line)

    if end_idx is None:
        return {}, text

    fm: dict[str, str] = {}
    for line in fm_lines:
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip('"')

    body = "\n".join(lines[end_idx + 1 :])
    return fm, body


def _get_source_url(fm: dict[str, str]) -> str:
    """Return source_url; fall back to source_url_1 for fee docs."""
    return fm.get("source_url") or fm.get("source_url_1", "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_h1(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    return "Unknown"


def _section_slug(heading: str) -> str:
    """'Exit Load' → 'exit_load', 'Who\\'s involved' → 'who_s_involved'."""
    slug = re.sub(r"[^a-z0-9]+", "_", heading.lower())
    return slug.strip("_")


def _determine_doc_type(file_path: Path) -> str:
    parts = {p.lower() for p in file_path.parts}
    if "fees" in parts:
        return "fee"
    return "factsheet"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_markdown_file(file_path: Path) -> list[dict[str, Any]]:
    """
    Split one markdown file into per-H2-section chunks.

    Returns a list of dicts, each with keys:
      text      — summary prefix + heading + section body
      metadata  — fund_name, doc_type, section, source_url, chunk_index, file_name
      doc_id    — "<stem>_<section_slug>"
    """
    raw = file_path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(raw)

    fund_name = _extract_h1(body)
    doc_type = _determine_doc_type(file_path)
    source_url = _get_source_url(fm)
    file_name = file_path.name
    stem = file_path.stem

    # Find all ## headings and their start positions in the body
    h2_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    matches = list(h2_pattern.finditer(body))

    if not matches:
        # No H2 sections — treat entire body as one chunk
        slug = "main"
        summary = (
            f"Document: {fund_name} | Section: {slug} | Source: {source_url}"
        )
        return [
            {
                "text": f"{summary}\n\n{body.strip()}",
                "metadata": {
                    "fund_name": fund_name,
                    "doc_type": doc_type,
                    "section": slug,
                    "source_url": source_url,
                    "chunk_index": 0,
                    "file_name": file_name,
                },
                "doc_id": f"{stem}_{slug}",
            }
        ]

    chunks: list[dict[str, Any]] = []
    for i, match in enumerate(matches):
        heading_text = match.group(1).strip()
        section = _section_slug(heading_text)

        # Section body: from end of this ## line to start of the next ## heading
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_body = body[body_start:body_end].strip()

        summary = (
            f"Document: {fund_name} | Section: {section} | Source: {source_url}"
        )
        chunk_text = f"{summary}\n\n## {heading_text}\n{section_body}"

        chunks.append(
            {
                "text": chunk_text,
                "metadata": {
                    "fund_name": fund_name,
                    "doc_type": doc_type,
                    "section": section,
                    "source_url": source_url,
                    "chunk_index": i,
                    "file_name": file_name,
                },
                "doc_id": f"{stem}_{section}",
            }
        )

    return chunks


def chunk_all_sources(
    factsheets_dir: Path,
    fees_dir: Path,
) -> list[dict[str, Any]]:
    """Chunk every .md in factsheets_dir and fees_dir; return combined list."""
    all_chunks: list[dict[str, Any]] = []
    for md_file in sorted(factsheets_dir.glob("*.md")):
        all_chunks.extend(chunk_markdown_file(md_file))
    for md_file in sorted(fees_dir.glob("*.md")):
        all_chunks.extend(chunk_markdown_file(md_file))
    return all_chunks
