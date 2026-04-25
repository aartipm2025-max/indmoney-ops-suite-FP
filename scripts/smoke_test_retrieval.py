import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pillars.pillar_a_knowledge.retriever import HybridRetriever
from pillars.pillar_a_knowledge.reranker import CrossEncoderReranker

retriever = HybridRetriever(Path("data/chroma_db"), Path("data/bm25_index"))
results = retriever.retrieve("What is the exit load for SBI Bluechip Fund?", top_k=10)
print(f"Retrieved {len(results)} chunks")
for r in results[:5]:
    did = r.get("doc_id", "unknown")
    score = r.get("rrf_score", 0)
    print(f"  {did} rrf={score:.4f}")

reranker = CrossEncoderReranker()
reranked = reranker.rerank("What is the exit load for SBI Bluechip Fund?", results, top_k=3)
print(f"Reranked to {len(reranked)} chunks")
for r in reranked:
    did = r.get("doc_id", "unknown")
    score = r.get("rerank_score", 0)
    print(f"  {did} rerank={score:.4f}")
