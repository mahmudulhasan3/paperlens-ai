from rank_bm25 import BM25Okapi

from paperlens.indexing.vector_store import get_collection


# Phase 3 (BM25): turn text into lowercase words, with punctuation removed
def tokenize(text):
    text = text.lower()
    cleaned = ""

    for ch in text:
        if ch.isalnum():
            cleaned = cleaned + ch
        else:
            cleaned = cleaned + " "

    return cleaned.split()


# Phase 3 (BM25): build a keyword index from the chunks of one owner only
def build_bm25_index(owner_id):
    data = get_collection().get(
        where={"owner_id": owner_id},
        include=["documents", "metadatas"],
    )

    tokenized_docs = []
    for text in data["documents"]: #type: ignore
        tokenized_docs.append(tokenize(text))

    return {
        "bm25": BM25Okapi(tokenized_docs),
        "ids": data["ids"],
        "texts": data["documents"],
        "metadatas": data["metadatas"],
    }


# Phase 3 (BM25): find the chunks that match the exact words of the question
def bm25_search(index, question, top_k=10):
    scores = index["bm25"].get_scores(tokenize(question))

    pairs = []
    for i in range(len(scores)):
        pairs.append((scores[i], i))
    pairs.sort(reverse=True)

    hits = []
    for score, i in pairs[:top_k]:
        if score > 0:
            hits.append(
                {
                    "chunk_id": index["ids"][i],
                    "text": index["texts"][i],
                    "metadata": index["metadatas"][i],
                    "score": score,
                }
            )

    return hits
