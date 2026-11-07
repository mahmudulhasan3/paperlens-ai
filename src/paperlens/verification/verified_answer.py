from paperlens.indexing.bm25_index import build_bm25_index
from paperlens.retrieval.hybrid import hybrid_search
from paperlens.generation.prompts import build_prompt, ABSTAIN_TEXT
from paperlens.generation.answer import find_citations
from paperlens.generation.llm import generate_text
from paperlens.verification.claim_extractor import extract_claims
from paperlens.verification.verifier import verify_claims


# Phase 6 (Abstention): the result when there is not enough verified evidence
def make_abstain(reason, claims, tokens, latency):
    return {
        "answer": ABSTAIN_TEXT,
        "abstained": True,
        "reason": reason,
        "claims": claims,
        "citations": [],
        "removed_claims": 0,
        "total_tokens": tokens,
        "total_latency": round(latency, 2),
    }


# Phase 6 (Evidence): turn source numbers into readable document and page references
def format_pages(numbers, pool):
    parts = []

    for number in numbers:
        meta = pool[number - 1]["metadata"]
        parts.append(
            meta["filename"]
            + " p. "
            + str(meta["page_start"])
            + "-"
            + str(meta["page_end"])
        )

    return parts


# Phase 6 (Final response): hybrid retrieval, answer, claim extraction, verification, then only verified claims
def answer_verified(question, owner_id, top_k=5):
    bm25_index = build_bm25_index(owner_id)
    chunks = hybrid_search(question, bm25_index, owner_id, top_k=top_k)

    if len(chunks) == 0:
        return make_abstain("no evidence found", [], 0, 0.0)

    # Step 1: write a draft answer from the evidence
    draft = generate_text(build_prompt(question, chunks))
    answer = draft["text"].strip()
    tokens = draft["prompt_tokens"] + draft["output_tokens"]
    latency = draft["latency"]

    if ABSTAIN_TEXT in answer:
        return make_abstain(
            "the model found no answer in the evidence", [], tokens, latency
        )

    # Step 2: break the draft into single claims
    extracted = extract_claims(answer)
    claims = extracted["claims"]
    tokens = tokens + extracted["prompt_tokens"] + extracted["output_tokens"]
    latency = latency + extracted["latency"]

    if len(claims) == 0:
        return make_abstain(
            "claims could not be extracted, so the answer could not be verified",
            [],
            tokens,
            latency,
        )

    # Step 3: verify every claim and validate its citations
    checked = verify_claims(claims, owner_id, chunks)
    pool = checked["pool"]
    tokens = tokens + checked["prompt_tokens"] + checked["output_tokens"]
    latency = latency + checked["latency"]

    # Step 4: build the final answer from verified claims only
    lines = []
    table = []
    removed = 0

    for verdict in checked["verdicts"]:
        table.append(
            {
                "claim": verdict["claim"],
                "status": verdict["status"],
                "evidence": format_pages(verdict["supporting"], pool),
                "invalid_citations": verdict["invalid_citations"],
            }
        )

        if verdict["status"] == "unsupported":
            removed = removed + 1
            continue

        marks = ""
        for number in verdict["supporting"]:
            marks = marks + "[" + str(number) + "]"

        line = "- " + verdict["claim"] + " " + marks
        if verdict["status"] == "partially_supported":
            line = line + " (partially supported)"
        lines.append(line)

    if len(lines) == 0:
        return make_abstain("no claim could be verified", table, tokens, latency)

    final_answer = "\n".join(lines)

    return {
        "answer": final_answer,
        "abstained": False,
        "reason": "",
        "claims": table,
        "citations": find_citations(final_answer, pool),
        "removed_claims": removed,
        "total_tokens": tokens,
        "total_latency": round(latency, 2),
    }
