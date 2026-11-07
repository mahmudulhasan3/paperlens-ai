import hashlib
import os
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from paperlens.ingestion.pipeline import ingest_pdf
from paperlens.indexing.vector_store import add_chunks, count_chunks, find_document
from paperlens.indexing.bm25_index import build_bm25_index
from paperlens.retrieval.hybrid import hybrid_search
from paperlens.generation.answer import answer_baseline
from paperlens.indexing.vector_store import list_documents
from paperlens.modes.summarize import summarize_document
from paperlens.modes.compare import compare_documents

app = FastAPI(title="PaperLens-AI")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# API state: one keyword index per owner, rebuilt after that owner uploads a new PDF
state = {"indexes": {}}


# API step: the request body for /ask
class AskRequest(BaseModel):
    owner_id: str
    question: str
    top_k: int = 5


# API step: the request body for /answer
class AnswerRequest(BaseModel):
    owner_id: str
    question: str
    top_k: int = 5


# API step: receive a PDF from one owner, process it and store its chunks
@app.post("/upload")
async def upload_pdf(owner_id: str = Form(...), file: UploadFile = File(...)):
    if owner_id.strip() == "":
        raise HTTPException(status_code=400, detail="owner_id is required")
    if not file.filename.lower().endswith(".pdf"): #type: ignore
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # Do not process the same file twice for the same owner
    existing = find_document(owner_id, file_hash)
    if existing is not None:
        return {
            "duplicate": True,
            "doc_id": existing["doc_id"],
            "filename": existing["filename"],
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
    state["indexes"].pop(owner_id, None)

    return {
        "duplicate": False,
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks": len(chunks),
    }


# API step: return the best evidence chunks using only the asking owner's documents
@app.post("/ask")
def ask(body: AskRequest):
    if count_chunks(body.owner_id) == 0:
        raise HTTPException(status_code=400, detail="Upload a PDF first")

    if body.owner_id not in state["indexes"]:
        state["indexes"][body.owner_id] = build_bm25_index(body.owner_id)

    hits = hybrid_search(
        body.question,
        state["indexes"][body.owner_id],
        body.owner_id,
        top_k=body.top_k,
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


# API step: baseline RAG answer (dense search + Gemini) using only the asking owner's documents
@app.post("/answer")
def answer(body: AnswerRequest):
    if count_chunks(body.owner_id) == 0:
        raise HTTPException(status_code=400, detail="Upload a PDF first")

    try:
        return answer_baseline(body.question, body.owner_id, top_k=body.top_k)
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))


# API step: the request body for /summarize
class SummarizeRequest(BaseModel):
    owner_id: str
    doc_id: str


# API step: list the documents of one owner
@app.get("/documents")
def documents(owner_id: str):
    return {"documents": list_documents(owner_id)}


# API step: structured summary of one document (Map-Reduce)
@app.post("/summarize")
def summarize(body: SummarizeRequest):
    try:
        return summarize_document(body.owner_id, body.doc_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))


# API step: the request body for /compare
class CompareRequest(BaseModel):
    owner_id: str
    doc_ids: list[str]


# API step: compare two or more documents of one owner
@app.post("/compare")
def compare(body: CompareRequest):
    try:
        return compare_documents(body.owner_id, body.doc_ids)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="LLM error: " + str(error))
