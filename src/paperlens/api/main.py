import hashlib
import os
import uuid

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from paperlens.api.routes.auth import router as auth_router
from paperlens.auth.dependencies import get_current_user
from paperlens.db.database import get_db
from paperlens.db.models import User, Document
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
app.include_router(auth_router)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# API state: one keyword index per user, rebuilt after that user uploads a new PDF
state = {"indexes": {}}


# API step: request bodies (the user comes from the token, never from the request)
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


# API step: the owner id used inside ChromaDB is the id of the logged-in user
def owner_of(user):
    return str(user.id)


# API step: receive a PDF from the logged-in user, process it and store its chunks
@app.post("/upload")
def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    owner_id = owner_of(current_user)
    content = file.file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # Do not process the same file twice for the same user
    existing = db.execute(
        select(Document).where(
            Document.user_id == current_user.id, Document.file_hash == file_hash
        )
    ).scalar_one_or_none()

    if existing is not None:
        return {
            "duplicate": True,
            "doc_id": existing.doc_id,
            "filename": existing.filename,
            "chunks": 0,
        }

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

    document = Document(
        doc_id=doc_id,
        user_id=current_user.id,
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

    state["indexes"].pop(owner_id, None)

    return {
        "duplicate": False,
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks": len(chunks),
    }


# API step: list the documents of the logged-in user
@app.get("/documents")
def documents(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = (
        db.execute(
            select(Document)
            .where(Document.user_id == current_user.id)
            .order_by(Document.created_at)
        )
        .scalars()
        .all()
    )

    result = []
    for row in rows:
        result.append(
            {"doc_id": row.doc_id, "filename": row.filename, "chunks": row.num_chunks}
        )

    return {"documents": result}


# API step: return the best evidence chunks from the user's own documents
@app.post("/ask")
def ask(body: AskRequest, current_user: User = Depends(get_current_user)):
    owner_id = owner_of(current_user)

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
def answer(body: AskRequest, current_user: User = Depends(get_current_user)):
    owner_id = owner_of(current_user)

    if count_chunks(owner_id) == 0:
        raise HTTPException(status_code=400, detail="Upload a PDF first")

    try:
        return answer_baseline(body.question, owner_id, top_k=body.top_k)
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))


# API step: structured summary of one of the user's documents
@app.post("/summarize")
def summarize(body: SummarizeRequest, current_user: User = Depends(get_current_user)):
    try:
        return summarize_document(owner_of(current_user), body.doc_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))


# API step: compare two or more of the user's documents
@app.post("/compare")
def compare(body: CompareRequest, current_user: User = Depends(get_current_user)):
    try:
        return compare_documents(owner_of(current_user), body.doc_ids)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))


# API step: extract one kind of information from one of the user's documents
@app.post("/extract")
def extract(body: ExtractRequest, current_user: User = Depends(get_current_user)):
    if body.request.strip() == "":
        raise HTTPException(status_code=400, detail="Write what you want to extract")

    try:
        return extract_from_document(owner_of(current_user), body.doc_id, body.request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))


# API step: one entry point, the router picks Q&A, Summarize, Compare or Extract
@app.post("/chat")
def chat(body: ChatRequest, current_user: User = Depends(get_current_user)):
    if body.message.strip() == "":
        raise HTTPException(status_code=400, detail="Write a message")

    try:
        return route_message(owner_of(current_user), body.message)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))
