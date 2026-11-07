import json
import os

from paperlens.ingestion.pipeline import ingest_pdf
from paperlens.indexing.vector_store import add_chunks, get_collection, search
from paperlens.indexing.bm25_index import build_bm25_index
from paperlens.retrieval.hybrid import hybrid_search

PDF_FOLDER = "data/golden/pdfs"
QUESTION_FILE = "data/golden/auto_questions.json"
RESULT_FILE = "evaluation/results_retrieval.json"
EVAL_OWNER = "eval"
TOP_K = 10


# Evaluation step 2 (Setup): index every evaluation PDF under a special eval owner
def index_eval_pdfs():
    get_collection().delete(where={"owner_id": EVAL_OWNER})
    doc_number = 0

    for filename in sorted(os.listdir(PDF_FOLDER)):
        if not filename.lower().endswith(".pdf"):
            continue

        doc_number = doc_number + 1
        path = os.path.join(PDF_FOLDER, filename)
        doc_id = "eval_" + str(doc_number)

        chunks = ingest_pdf(path, doc_id, EVAL_OWNER, doc_id + "_hash", filename)
        add_chunks(chunks)


# Evaluation step 2 (Matching): a chunk is relevant if it is in the right document and overlaps the supporting pages
def is_relevant(item, meta):
    if meta["filename"] != item["document"]:
        return False
    if meta["page_end"] < item["supporting_page_start"]:
        return False
    if meta["page_start"] > item["supporting_page_end"]:
        return False
    return True


# Evaluation step 2 (Matching): the rank of the first relevant chunk, or 0 if there is none
def find_rank(item, hits):
    for i in range(len(hits)):
        if is_relevant(item, hits[i]["metadata"]):
            return i + 1
    return 0


# Evaluation step 2 (Metrics): turn a list of ranks into Hit@1, Hit@5 and MRR
def summarize(ranks):
    total = len(ranks)
    hit1 = 0
    hit5 = 0
    rr_sum = 0.0

    for rank in ranks:
        if rank == 1:
            hit1 = hit1 + 1
        if rank >= 1 and rank <= 5:
            hit5 = hit5 + 1
        if rank > 0:
            rr_sum = rr_sum + 1 / rank

    return {
        "questions": total,
        "hit_at_1": round(hit1 / total, 3),
        "hit_at_5": round(hit5 / total, 3),
        "mrr": round(rr_sum / total, 3),
    }


# Evaluation step 2 (Run): compare dense-only baseline with hybrid retrieval on all answerable questions
def main():
    with open(QUESTION_FILE) as f:
        all_questions = json.load(f)

    questions = []
    for item in all_questions:
        if item["answerable"]:
            questions.append(item)

    if len(questions) == 0:
        print("No answerable questions found in", QUESTION_FILE)
        return

    index_eval_pdfs()
    bm25_index = build_bm25_index(EVAL_OWNER)

    dense_ranks = []
    hybrid_ranks = []

    for item in questions:
        dense_hits = search(item["question"], EVAL_OWNER, top_k=TOP_K)
        hybrid_hits = hybrid_search(
            item["question"], bm25_index, EVAL_OWNER, top_k=TOP_K
        )

        dense_ranks.append(find_rank(item, dense_hits))
        hybrid_ranks.append(find_rank(item, hybrid_hits))

    results = {
        "dense_baseline": summarize(dense_ranks),
        "hybrid": summarize(hybrid_ranks),
    }

    print("Questions:", len(questions))
    print("Dense baseline:", results["dense_baseline"])
    print("Hybrid:        ", results["hybrid"])

    with open(RESULT_FILE, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
