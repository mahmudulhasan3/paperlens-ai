from sqlalchemy import delete, func, select

from paperlens.db.database import SessionLocal
from paperlens.db.models import Chunk
from paperlens.indexing.embeddings import embed_texts, embed_query

# Phase 2 (Vector store): the details of a chunk, in the same shape that the rest of the project already uses
def to_metadata(row):
    return {
        "doc_id": row.doc_id,
        "owner_id": row.owner_id,
        "file_hash": row.file_hash,
        "filename": row.filename,
        "chunk_index": row.chunk_index,
        "section": row.section,
        "page_start": row.page_start,
        "page_end": row.page_end,
        "word_count": row.word_count,
    }


# Phase 2 (Vector store): embed every chunk and save it in the chunks table (saving the same chunk again replaces it)
def add_chunks(chunks):
    texts = []
    for chunk in chunks:
        texts.append(chunk["text"])

    embeddings = embed_texts(texts)

    with SessionLocal() as db:
        for i in range(len(chunks)):
            chunk = chunks[i]
            db.merge(
                Chunk(
                    chunk_id=chunk["chunk_id"],
                    doc_id=chunk["doc_id"],
                    owner_id=chunk["owner_id"],
                    file_hash=chunk["file_hash"],
                    filename=chunk["filename"],
                    chunk_index=chunk["chunk_index"],
                    section=chunk["section"],
                    page_start=chunk["page_start"],
                    page_end=chunk["page_end"],
                    word_count=chunk["word_count"],
                    text=chunk["text"],
                    embedding=embeddings[i],
                )
            )
        db.commit()


# Phase 2 (Metadata filtering): count how many chunks one owner has
def count_chunks(owner_id):
    with SessionLocal() as db:
        return db.execute(
            select(func.count(Chunk.chunk_id)).where(Chunk.owner_id == owner_id)
        ).scalar()


# Phase 2 (Vector store): find the chunks closest in meaning, only inside one owner's documents
def search(question, owner_id, top_k=5):
    query_vector = embed_query(question)
    hits = []

    with SessionLocal() as db:
        distance = Chunk.embedding.cosine_distance(query_vector)
        rows = db.execute(
            select(Chunk, distance.label("distance"))
            .where(Chunk.owner_id == owner_id)
            .order_by(distance)
            .limit(top_k)
        ).all()

        for row in rows:
            chunk = row[0]
            hits.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "metadata": to_metadata(chunk),
                    "distance": float(row[1]),
                }
            )

    return hits


# Phase 5 (Compare): find the closest chunks inside one single document of one owner
def search_document(question, owner_id, doc_id, top_k=3):
    query_vector = embed_texts([question])[0]
    hits = []

    with SessionLocal() as db:
        distance = Chunk.embedding.cosine_distance(query_vector)
        rows = db.execute(
            select(Chunk, distance.label("distance"))
            .where(Chunk.owner_id == owner_id, Chunk.doc_id == doc_id)
            .order_by(distance)
            .limit(top_k)
        ).all()

        for row in rows:
            chunk = row[0]
            hits.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "metadata": to_metadata(chunk),
                    "distance": float(row[1]),
                }
            )

    return hits


# Phase 4 (Summarization): the documents of one owner, so the user can pick one
def list_documents(owner_id):
    with SessionLocal() as db:
        rows = db.execute(
            select(Chunk.doc_id, Chunk.filename)
            .where(Chunk.owner_id == owner_id)
            .distinct()
            .order_by(Chunk.filename)
        ).all()

    result = []
    for row in rows:
        result.append({"doc_id": row[0], "filename": row[1]})

    return result


# Phase 4 (Summarization): get every chunk of one document, in reading order
def get_document_chunks(owner_id, doc_id):
    chunks = []

    with SessionLocal() as db:
        rows = (
            db.execute(
                select(Chunk)
                .where(Chunk.owner_id == owner_id, Chunk.doc_id == doc_id)
                .order_by(Chunk.chunk_index)
            )
            .scalars()
            .all()
        )

        for row in rows:
            chunks.append(
                {
                    "chunk_id": row.chunk_id,
                    "text": row.text,
                    "metadata": to_metadata(row),
                }
            )

    return chunks


# Phase 3 (BM25): all chunks of one owner, as lists of ids, texts and details
def get_owner_chunks(owner_id):
    data = {"ids": [], "documents": [], "metadatas": []}

    with SessionLocal() as db:
        rows = (
            db.execute(
                select(Chunk).where(Chunk.owner_id == owner_id).order_by(Chunk.chunk_id)
            )
            .scalars()
            .all()
        )

        for row in rows:
            data["ids"].append(row.chunk_id)
            data["documents"].append(row.text)
            data["metadatas"].append(to_metadata(row))

    return data


# Vector store: delete the chunks of one document of one owner
def delete_document_chunks(owner_id, doc_id):
    with SessionLocal() as db:
        db.execute(
            delete(Chunk).where(Chunk.owner_id == owner_id, Chunk.doc_id == doc_id)
        )
        db.commit()


# Vector store: delete all chunks of one owner
def delete_owner_chunks(owner_id):
    with SessionLocal() as db:
        db.execute(delete(Chunk).where(Chunk.owner_id == owner_id))
        db.commit()


# Vector store: delete the chunks of all guests (used when the server starts)
def delete_guest_chunks():
    with SessionLocal() as db:
        db.execute(delete(Chunk).where(Chunk.owner_id.like("guest:%")))
        db.commit()
