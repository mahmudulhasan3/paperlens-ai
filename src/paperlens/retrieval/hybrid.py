from paperlens.indexing.vector_store import search
from paperlens.indexing.bm25_index import bm25_search


# Phase 3 (RRF): give every chunk points based on its rank in one result list
def add_hits(combined, hits, rank_name, k):
    for i in range(len(hits)):
        hit = hits[i]
        chunk_id = hit["chunk_id"]

        if chunk_id not in combined:
            combined[chunk_id] = {
                "chunk_id": chunk_id,
                "text": hit["text"],
                "metadata": hit["metadata"],
                "rrf_score": 0.0,
                "dense_rank": None,
                "keyword_rank": None,
            }

        combined[chunk_id]["rrf_score"] = combined[chunk_id]["rrf_score"] + 1 / (
            k + i + 1
        )
        combined[chunk_id][rank_name] = i + 1


# Phase 3 (RRF): merge the dense list and the keyword list into one sorted list
def rrf_fuse(dense_hits, keyword_hits, k=60):
    combined = {}
    add_hits(combined, dense_hits, "dense_rank", k)
    add_hits(combined, keyword_hits, "keyword_rank", k)

    scored = []
    for chunk_id in combined:
        scored.append((combined[chunk_id]["rrf_score"], chunk_id))
    scored.sort(reverse=True)

    results = []
    for score, chunk_id in scored:
        results.append(combined[chunk_id])

    return results


# Phase 3 (Hybrid retrieval): run both searches inside one owner's documents and fuse them
def hybrid_search(question, bm25_index, owner_id, top_k=5, candidates=20):
    dense_hits = search(question, owner_id, top_k=candidates)
    keyword_hits = bm25_search(bm25_index, question, top_k=candidates)
    fused = rrf_fuse(dense_hits, keyword_hits)
    return fused[:top_k]
