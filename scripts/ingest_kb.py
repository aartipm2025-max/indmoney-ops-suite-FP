"""
scripts/ingest_kb.py

Phase 3 Sub-step 2: Run the full knowledge-base ingestion pipeline.
Chunks 6 markdown files → embeds → ChromaDB + BM25 index.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings  # noqa: F401  (validates env + provides config)
from core.logger import log
from pillars.pillar_a_knowledge.chunker import chunk_all_sources
from pillars.pillar_a_knowledge.ingest import ingest_knowledge_base

PROJECT_ROOT = Path(__file__).parent.parent

factsheets_dir = PROJECT_ROOT / "data" / "factsheets" / "markdown"
fees_dir = PROJECT_ROOT / "data" / "fees"
chroma_dir = PROJECT_ROOT / "data" / "chroma_db"
bm25_dir = PROJECT_ROOT / "data" / "bm25_index"


def main() -> None:
    log.info("ingest_kb: starting knowledge base ingestion")

    # Step 1 — chunk
    chunks = chunk_all_sources(factsheets_dir, fees_dir)
    log.info("ingest_kb: {} chunks produced", len(chunks))
    print(f"\nChunks created: {len(chunks)}")

    # Step 2 — ingest
    summary = ingest_knowledge_base(chunks, chroma_dir, bm25_dir)

    print(f"ChromaDB collection size: {summary['chroma_collection_size']}")
    print(f"BM25 index size:          {summary['bm25_corpus_size']}")
    print(f"Embedding model:          {summary['embedding_model']}\n")
    log.info("ingest_kb: done — {}", summary)


if __name__ == "__main__":
    main()
