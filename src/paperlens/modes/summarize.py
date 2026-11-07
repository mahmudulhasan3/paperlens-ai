import time

from paperlens.indexing.vector_store import get_document_chunks
from paperlens.generation.llm import generate_text

CHUNKS_PER_BATCH = 8

SUMMARY_PARTS = [
    "Research Problem",
    "Research Objectives",
    "Proposed Methodology",
    "Dataset",
    "Experimental Setup",
    "Key Findings",
    "Limitations",
    "Future Work",
]

NOT_STATED = "Not stated in the document."


# Phase 4 (Map step): split the chunks of one document into batches of 8
def make_batches(chunks):
    batches = []

    for start in range(0, len(chunks), CHUNKS_PER_BATCH):
        batches.append(chunks[start : start + CHUNKS_PER_BATCH])

    return batches


# Phase 4 (Map step): the instructions that turn one batch of chunks into short notes
def build_map_prompt(batch):
    text = ""

    for chunk in batch:
        meta = chunk["metadata"]
        header = (
            "["
            + meta["section"]
            + " | pages "
            + str(meta["page_start"])
            + "-"
            + str(meta["page_end"])
            + "]"
        )
        text = text + header + "\n" + chunk["text"] + "\n\n"

    prompt = "You are reading one part of a research paper.\n"
    prompt = (
        prompt
        + "Write short factual notes (at most 8 bullet points) about what this part says.\n"
    )
    prompt = prompt + "Rules:\n"
    prompt = prompt + "1. Use only the text below.\n"
    prompt = (
        prompt
        + "2. After each note, write the page in the form (p. 5) or (pp. 5-6), using the page numbers in the headers.\n"
    )
    prompt = (
        prompt
        + "3. If this part has no useful content, write: No relevant content.\n\n"
    )
    prompt = prompt + "TEXT:\n" + text + "NOTES:"

    return prompt


# Phase 4 (Reduce step): the instructions that turn all notes into one structured summary
def build_reduce_prompt(all_notes):
    prompt = "Below are notes taken from a research paper, in reading order.\n"
    prompt = (
        prompt
        + "Write a structured summary with exactly these headings, in this order:\n"
    )

    for part in SUMMARY_PARTS:
        prompt = prompt + "- " + part + "\n"

    prompt = prompt + "\nRules:\n"
    prompt = (
        prompt
        + "1. Use only the notes. Do not add anything that is not in the notes.\n"
    )
    prompt = (
        prompt + "2. Keep the page references from the notes, for example (p. 5).\n"
    )
    prompt = (
        prompt
        + "3. If the notes do not cover a heading, write exactly: "
        + NOT_STATED
        + "\n\n"
    )
    prompt = prompt + "NOTES:\n" + all_notes + "\n\nSUMMARY:"

    return prompt


# Phase 4 (Summarization): summarize one document with Map-Reduce
def summarize_document(owner_id, doc_id):
    chunks = get_document_chunks(owner_id, doc_id)

    if len(chunks) == 0:
        raise ValueError("Document not found")

    notes = []
    total_tokens = 0
    total_latency = 0.0

    # Map: one set of notes for every batch of chunks
    for batch in make_batches(chunks):
        result = generate_text(build_map_prompt(batch))
        notes.append(result["text"].strip())
        total_tokens = total_tokens + result["prompt_tokens"] + result["output_tokens"]
        total_latency = total_latency + result["latency"]
        time.sleep(2)

    # Reduce: one structured summary from all notes
    result = generate_text(build_reduce_prompt("\n\n".join(notes)))
    total_tokens = total_tokens + result["prompt_tokens"] + result["output_tokens"]
    total_latency = total_latency + result["latency"]

    return {
        "summary": result["text"].strip(),
        "batches": len(notes),
        "total_tokens": total_tokens,
        "total_latency": round(total_latency, 2),
    }
