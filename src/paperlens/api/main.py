import hashlib
import os
import uuid

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from paperlens.api.routes.auth import router as auth_router
from paperlens.auth.dependencies import get_actor
from paperlens.auth.guests import get_guest, purge_all_guest_data
from paperlens.db.database import Base, engine, get_db
from paperlens.db.models import Document
from paperlens.ingestion.pipeline import ingest_pdf
from paperlens.indexing.vector_store import add_chunks, count_chunks, get_collection
from paperlens.indexing.bm25_index import build_bm25_index
from paperlens.retrieval.hybrid import hybrid_search
from paperlens.generation.answer import answer_baseline
from paperlens.modes.summarize import summarize_document
from paperlens.modes.compare import compare_documents
from paperlens.modes.extract import extract_from_document
from paperlens.modes.router import route_message

app = FastAPI(title="PaperLens-AI")

# Database step: create the tables on startup if they do not exist yet
Base.metadata.create_all(engine)

# Guest step: guest data lives only until the application restarts
purge_all_guest_data()

app.include_router(auth_router)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# API state: one keyword index per owner, rebuilt after that owner uploads a new PDF
state = {"indexes": {}}


# API step: request bodies (the owner comes from the token, never from the request)
class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class SummarizeRequest(BaseModel):
    doc_id: str


class CompareRequest(BaseModel):
    doc_ids: list[str]


class ExtractRequest(BaseModel):
    doc_id: str
    request: str


class ChatRequest(BaseModel):
    message: str


# API step: the answer for a file that the same owner already uploaded
def duplicate_response(doc_id, filename):
    return {"duplicate": True, "doc_id": doc_id, "filename": filename, "chunks": 0}


# API step: receive a PDF from a guest or a user, process it and store its chunks
@app.post("/upload")
def upload_pdf(
    file: UploadFile = File(...),
    actor: dict = Depends(get_actor),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    owner_id = actor["owner_id"]
    is_guest = actor["kind"] == "guest"
    content = file.file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # Do not process the same file twice for the same owner
    if is_guest:
        guest = get_guest(owner_id)
        for doc in guest["documents"]:
            if doc["file_hash"] == file_hash:
                return duplicate_response(doc["doc_id"], doc["filename"])
    else:
        existing = db.execute(
            select(Document).where(
                Document.user_id == actor["user"].id, Document.file_hash == file_hash
            )
        ).scalar_one_or_none()
        if existing is not None:
            return duplicate_response(existing.doc_id, existing.filename)

    doc_id = "doc_" + uuid.uuid4().hex[:8]
    save_path = os.path.join(UPLOAD_FOLDER, doc_id + ".pdf")

    with open(save_path, "wb") as f:
        f.write(content)

    try:
        chunks = ingest_pdf(save_path, doc_id, owner_id, file_hash, file.filename)
    except Exception as error:
        os.remove(save_path)
        raise HTTPException(
            status_code=400, detail="Could not process the PDF: " + str(error)
        )

    add_chunks(chunks)
    state["indexes"].pop(owner_id, None)

    # Guests keep nothing on disk, the chunks are enough and they are temporary
    if is_guest:
        os.remove(save_path)
        guest["documents"].append(
            {
                "doc_id": doc_id,
                "filename": file.filename,
                "file_hash": file_hash,
                "chunks": len(chunks),
            }
        )
        return {
            "duplicate": False,
            "doc_id": doc_id,
            "filename": file.filename,
            "chunks": len(chunks),
        }

    document = Document(
        doc_id=doc_id,
        user_id=actor["user"].id,
        filename=file.filename,
        file_hash=file_hash,
        num_chunks=len(chunks),
    )
    db.add(document)

    try:
        db.commit()
    except Exception:
        db.rollback()
        get_collection().delete(where={"doc_id": doc_id})
        os.remove(save_path)
        raise HTTPException(status_code=500, detail="Could not save the document")

    return {
        "duplicate": False,
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks": len(chunks),
    }


# API step: list the documents of the guest (temporary list) or of the registered user (database)
@app.get("/documents")
def documents(actor: dict = Depends(get_actor), db: Session = Depends(get_db)):
    result = []

    if actor["kind"] == "guest":
        for doc in get_guest(actor["owner_id"])["documents"]:
            result.append(
                {
                    "doc_id": doc["doc_id"],
                    "filename": doc["filename"],
                    "chunks": doc["chunks"],
                }
            )
        return {"documents": result}

    rows = (
        db.execute(
            select(Document)
            .where(Document.user_id == actor["user"].id)
            .order_by(Document.created_at)
        )
        .scalars()
        .all()
    )

    for row in rows:
        result.append(
            {"doc_id": row.doc_id, "filename": row.filename, "chunks": row.num_chunks}
        )

    return {"documents": result}


# API step: return the best evidence chunks from the owner's own documents
@app.post("/ask")
def ask(body: AskRequest, actor: dict = Depends(get_actor)):
    owner_id = actor["owner_id"]

    if count_chunks(owner_id) == 0:
        raise HTTPException(status_code=400, detail="Upload a PDF first")

    if owner_id not in state["indexes"]:
        state["indexes"][owner_id] = build_bm25_index(owner_id)

    hits = hybrid_search(
        body.question, state["indexes"][owner_id], owner_id, top_k=body.top_k
    )

    results = []
    for hit in hits:
        meta = hit["metadata"]
        results.append(
            {
                "filename": meta["filename"],
                "section": meta["section"],
                "page_start": meta["page_start"],
                "page_end": meta["page_end"],
                "text": hit["text"],
            }
        )

    return {"question": body.question, "results": results}


# API step: baseline RAG answer (dense search + Gemini), kept for the final comparison
@app.post("/answer")
def answer(body: AskRequest, actor: dict = Depends(get_actor)):
    owner_id = actor["owner_id"]

    if count_chunks(owner_id) == 0:
        raise HTTPException(status_code=400, detail="Upload a PDF first")

    try:
        return answer_baseline(body.question, owner_id, top_k=body.top_k)
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))


# API step: structured summary of one of the owner's documents
@app.post("/summarize")
def summarize(body: SummarizeRequest, actor: dict = Depends(get_actor)):
    try:
        return summarize_document(actor["owner_id"], body.doc_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))


# API step: compare two or more of the owner's documents
@app.post("/compare")
def compare(body: CompareRequest, actor: dict = Depends(get_actor)):
    try:
        return compare_documents(actor["owner_id"], body.doc_ids)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))


# API step: extract one kind of information from one of the owner's documents
@app.post("/extract")
def extract(body: ExtractRequest, actor: dict = Depends(get_actor)):
    if body.request.strip() == "":
        raise HTTPException(status_code=400, detail="Write what you want to extract")

    try:
        return extract_from_document(actor["owner_id"], body.doc_id, body.request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))


# API step: one entry point, the router picks Q&A, Summarize, Compare or Extract
@app.post("/chat")
def chat(body: ChatRequest, actor: dict = Depends(get_actor)):
    if body.message.strip() == "":
        raise HTTPException(status_code=400, detail="Write a message")

    try:
        return route_message(actor["owner_id"], body.message)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))
