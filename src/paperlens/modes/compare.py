from paperlens.indexing.vector_store import search_document
from paperlens.generation.prompts import build_context
from paperlens.generation.answer import find_citations
from paperlens.generation.llm import generate_text

NOT_STATED = "Not stated in the provided sources."

CRITERIA = [
    {
        "name": "Research Objectives",
        "query": "research objectives and goals of the paper",
    },
    {"name": "Problem Statement", "query": "the research problem the paper addresses"},
    {"name": "Methodology", "query": "proposed method or approach"},
    {"name": "Datasets", "query": "datasets used in the experiments"},
    {
        "name": "Experimental Settings",
        "query": "experimental setup, models and parameters",
    },
    {
        "name": "Performance Metrics",
        "query": "evaluation metrics used to measure performance",
    },
    {"name": "Results", "query": "main experimental results and findings"},
    {"name": "Limitations", "query": "limitations of the work"},
]


# Phase 5 (Compare): for every document and every criterion, collect the best chunks
def collect_evidence(owner_id, doc_ids, per_criterion=2):
    chunks = []
    seen = []
    names = []

    for doc_id in doc_ids:
        doc_found = False

        for criterion in CRITERIA:
            hits = search_document(
                criterion["query"], owner_id, doc_id, top_k=per_criterion
            )

            for hit in hits:
                if not doc_found:
                    names.append(hit["metadata"]["filename"])
                    doc_found = True

                if hit["chunk_id"] not in seen:
                    seen.append(hit["chunk_id"])
                    chunks.append(hit)

        if not doc_found:
            raise ValueError("Document not found: " + doc_id)

    return chunks, names


# Phase 5 (Compare): the instructions that ask Gemini for a criterion-by-criterion comparison
def build_compare_prompt(chunks, names):
    prompt = "You are comparing research papers.\n"
    prompt = prompt + "The papers are: " + ", ".join(names) + ".\n"
    prompt = (
        prompt
        + "Use ONLY the numbered sources below. Every source shows its paper name.\n\n"
    )
    prompt = prompt + "For each of these criteria, write a section:\n"

    for criterion in CRITERIA:
        prompt = prompt + "- " + criterion["name"] + "\n"

    prompt = prompt + "\nFormat of every section:\n"
    prompt = prompt + "### <criterion name>\n"
    prompt = (
        prompt
        + "- **<paper name>**: what this paper does, with source numbers like [1].\n"
    )
    prompt = prompt + "(one line for every paper)\n"
    prompt = (
        prompt
        + "- **Difference**: one sentence on the main difference between the papers.\n\n"
    )
    prompt = prompt + "Rules:\n"
    prompt = (
        prompt
        + "1. After every factual statement, add the source number in square brackets, for example [1].\n"
    )
    prompt = prompt + "2. Write two sources as [1][2]. Never write [1, 2].\n"
    prompt = prompt + "3. Do not use any knowledge from outside the sources.\n"
    prompt = (
        prompt
        + "4. If the sources of a paper do not cover a criterion, write exactly: "
        + NOT_STATED
        + "\n\n"
    )
    prompt = prompt + "SOURCES:\n" + build_context(chunks) + "\n"
    prompt = prompt + "COMPARISON:"

    return prompt


# Phase 5 (Compare): compare two or more documents of one owner
def compare_documents(owner_id, doc_ids):
    if len(doc_ids) < 2:
        raise ValueError("Choose at least two documents to compare")

    chunks, names = collect_evidence(owner_id, doc_ids)
    result = generate_text(build_compare_prompt(chunks, names))
    comparison = result["text"].strip()

    return {
        "comparison": comparison,
        "documents": names,
        "citations": find_citations(comparison, chunks),
        "prompt_tokens": result["prompt_tokens"],
        "output_tokens": result["output_tokens"],
        "latency": result["latency"],
    }
