import chromadb

from paperlens.indexing.embeddings import embed_texts

# Phase 2 (Vector store): ChromaDB saves its data in the chroma_db/ folder
client = chromadb.PersistentClient(path="chroma_db")


# Phase 2 (Vector store): open the collection (like a table), or create it the first time
def get_collection():
    return client.get_or_create_collection(
        name="paperlens_chunks",
        metadata={"hnsw:space": "cosine"},
    )


# Phase 2 (Vector store): embed every chunk and store it with its metadata
def add_chunks(chunks):
    collection = get_collection()

    ids = []
    texts = []
    metadatas = []

    for chunk in chunks:
        ids.append(chunk["chunk_id"])
        texts.append(chunk["text"])
        metadatas.append(
            {
                "doc_id": chunk["doc_id"],
                "owner_id": chunk["owner_id"],
                "file_hash": chunk["file_hash"],
                "filename": chunk["filename"],
                "chunk_index": chunk["chunk_index"],
                "section": chunk["section"],
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "word_count": chunk["word_count"],
            }
        )

    embeddings = embed_texts(texts)

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )


# Phase 2 (Metadata filtering): count how many chunks one owner has
def count_chunks(owner_id):
    data = get_collection().get(where={"owner_id": owner_id}, include=[])
    return len(data["ids"])


# Phase 2 (Metadata filtering): check if this owner already uploaded the same file
def find_document(owner_id, file_hash):
    data = get_collection().get(
        where={"$and": [{"owner_id": owner_id}, {"file_hash": file_hash}]},
        include=["metadatas"],
    )

    if len(data["ids"]) == 0:
        return None
    return data["metadatas"][0]  # type: ignore


# Phase 2 (Vector store): find the chunks closest in meaning, only inside one owner's documents
def search(question, owner_id, top_k=5):
    collection = get_collection()
    query_vector = embed_texts([question])

    results = collection.query(
        query_embeddings=query_vector,
        n_results=top_k,
        where={"owner_id": owner_id},
    )

    hits = []
    for i in range(len(results["ids"][0])):
        hits.append(
            {
                "chunk_id": results["ids"][0][i],
                "text": results["documents"][0][i],  # type: ignore
                "metadata": results["metadatas"][0][i],  # type: ignore
                "distance": results["distances"][0][i],  # type: ignore
            }
        )

    return hits


# Phase 4 (Summarization): get every chunk of one document, in reading order
def get_document_chunks(owner_id, doc_id):
    data = get_collection().get(
        where={"$and": [{"owner_id": owner_id}, {"doc_id": doc_id}]},
        include=["documents", "metadatas"],
    )

    pairs = []
    for i in range(len(data["ids"])):
        meta = data["metadatas"][i]
        pairs.append(
            (
                meta["chunk_index"],
                {
                    "chunk_id": data["ids"][i],
                    "text": data["documents"][i],
                    "metadata": meta,
                },
            )
        )

    pairs.sort()

    chunks = []
    for index, chunk in pairs:
        chunks.append(chunk)

    return chunks


# Phase 4 (Summarization): list the documents of one owner, so the user can pick one
def list_documents(owner_id):
    data = get_collection().get(where={"owner_id": owner_id}, include=["metadatas"])

    names = {}
    for meta in data["metadatas"]:
        names[meta["doc_id"]] = meta["filename"]

    result = []
    for doc_id in names:
        result.append({"doc_id": doc_id, "filename": names[doc_id]})

    return result


# Phase 5 (Compare): find the closest chunks inside one single document
def search_document(question, owner_id, doc_id, top_k=3):
    collection = get_collection()
    query_vector = embed_texts([question])

    results = collection.query(
        query_embeddings=query_vector,
        n_results=top_k,
        where={"$and": [{"owner_id": owner_id}, {"doc_id": doc_id}]},
    )

    hits = []
    for i in range(len(results["ids"][0])):
        hits.append(
            {
                "chunk_id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
            }
        )

    return hits
