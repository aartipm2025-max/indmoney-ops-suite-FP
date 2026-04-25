"""
pillars/pillar_a_knowledge/ingest.py

Load chunked documents into ChromaDB (dense) and BM25 (sparse) indexes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import bm25s
import chromadb
from sentence_transformers import SentenceTransformer

from core.logger import log

COLLECTION_NAME = "sbi_mf_knowledge"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


def ingest_knowledge_base(
    chunks: list[dict[str, Any]],
    chroma_persist_dir: Path,
    bm25_persist_dir: Path,
) -> dict[str, Any]:
    """
    Embed chunks, store in ChromaDB, and build + save a BM25 index.

    Returns a summary dict with counts and model name.
    """
    # ------------------------------------------------------------------
    # 1. ChromaDB — create/reset persistent collection
    # ------------------------------------------------------------------
    log.info("ingest: initialising ChromaDB at {}", chroma_persist_dir)
    chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_persist_dir))

    try:
        client.delete_collection(COLLECTION_NAME)
        log.info("ingest: dropped existing collection '{}'", COLLECTION_NAME)
    except Exception:
        pass  # collection did not exist yet

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    log.info("ingest: created collection '{}'", COLLECTION_NAME)

    # ------------------------------------------------------------------
    # 2. Load embedding model
    # ------------------------------------------------------------------
    log.info("ingest: loading embedding model '{}'", EMBEDDING_MODEL)
    model = SentenceTransformer(EMBEDDING_MODEL)
    log.info("ingest: model ready")

    # ------------------------------------------------------------------
    # 3. Embed all chunks and add to ChromaDB
    # ------------------------------------------------------------------
    texts = [c["text"] for c in chunks]
    log.info("ingest: embedding {} chunks (this may take a moment)", len(texts))
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True,
        batch_size=32,
    )

    ids = [c["doc_id"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=[e.tolist() for e in embeddings],
        metadatas=metadatas,
    )
    chroma_size = collection.count()
    log.info("ingest: ChromaDB collection size = {}", chroma_size)

    # ------------------------------------------------------------------
    # 4. BM25 index — build and persist
    # ------------------------------------------------------------------
    log.info("ingest: building BM25 index")
    # Corpus stored as dicts so doc_id is preserved for retrieval
    corpus_dicts = [{"text": c["text"], "doc_id": c["doc_id"]} for c in chunks]
    corpus_texts = [d["text"] for d in corpus_dicts]

    token_corpus = bm25s.tokenize(corpus_texts, show_progress=False)
    retriever = bm25s.BM25(corpus=corpus_dicts)
    retriever.index(token_corpus, show_progress=False)

    bm25_persist_dir.mkdir(parents=True, exist_ok=True)
    retriever.save(str(bm25_persist_dir), corpus=corpus_dicts)
    log.info("ingest: BM25 index saved to {}", bm25_persist_dir)

    return {
        "total_chunks": len(chunks),
        "chroma_collection_size": chroma_size,
        "bm25_corpus_size": len(corpus_dicts),
        "embedding_model": EMBEDDING_MODEL,
    }
