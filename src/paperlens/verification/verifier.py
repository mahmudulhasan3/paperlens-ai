import json

from paperlens.indexing.vector_store import search
from paperlens.generation.prompts import build_context
from paperlens.generation.llm import generate_text

STATUSES = ["supported", "partially_supported", "unsupported"]


# Phase 6 (Evidence matching): collect candidate sources for every claim, without trusting the answer's citations
def match_evidence(claims, owner_id, answer_chunks, per_claim=3):
    pool = list(answer_chunks)
    pool_ids = []
    for chunk in pool:
        pool_ids.append(chunk["chunk_id"])

    candidates = []

    for claim in claims:
        numbers = []

        for number in claim["cited"]:
            if number >= 1 and number <= len(answer_chunks) and number not in numbers:
                numbers.append(number)

        for hit in search(claim["claim"], owner_id, top_k=per_claim):
            if hit["chunk_id"] not in pool_ids:
                pool.append(hit)
                pool_ids.append(hit["chunk_id"])

            number = pool_ids.index(hit["chunk_id"]) + 1
            if number not in numbers:
                numbers.append(number)

        candidates.append(numbers)

    return pool, candidates


# Phase 6 (Claim verification): the instructions that ask Gemini to judge every claim
def build_verify_prompt(claims, candidates, pool):
    prompt = "You verify factual claims against numbered sources.\n"
    prompt = prompt + "For every claim, choose one status:\n"
    prompt = prompt + "supported: the sources fully support the claim.\n"
    prompt = (
        prompt
        + "partially_supported: the sources support only part of the claim, or leave important details unverified.\n"
    )
    prompt = prompt + "unsupported: the sources do not support the claim.\n"
    prompt = prompt + "Rules:\n"
    prompt = prompt + "1. For each claim, use ONLY the sources listed for that claim.\n"
    prompt = (
        prompt + "2. Judge only from the source text. Do not use outside knowledge.\n"
    )
    prompt = (
        prompt
        + "3. List in supporting the numbers of the sources that actually support the claim. Use an empty list if none.\n"
    )
    prompt = prompt + "Reply with only a JSON list, nothing else, in this form:\n"
    prompt = prompt + '[{"id": 1, "status": "supported", "supporting": [2]}]\n\n'
    prompt = prompt + "CLAIMS:\n"

    for i in range(len(claims)):
        numbers = []
        for number in candidates[i]:
            numbers.append(str(number))
        prompt = (
            prompt
            + str(i + 1)
            + ". "
            + claims[i]["claim"]
            + " (sources: "
            + ", ".join(numbers)
            + ")\n"
        )

    prompt = prompt + "\nSOURCES:\n" + build_context(pool) + "\nVERDICTS:"

    return prompt


# Phase 6 (Claim verification): read Gemini's verdicts, and treat anything unclear as unsupported
def parse_verdicts(reply, claims, candidates):
    found = {}

    start = reply.find("[")
    end = reply.rfind("]")
    if start != -1 and end != -1:
        try:
            data = json.loads(reply[start : end + 1])
        except ValueError:
            data = []

        for item in data:
            if not isinstance(item, dict):
                continue

            claim_id = item.get("id")
            status = item.get("status")
            if not isinstance(claim_id, int) or status not in STATUSES:
                continue
            if claim_id < 1 or claim_id > len(claims):
                continue

            supporting = []
            for number in item.get("supporting", []):
                if isinstance(number, int) and number in candidates[claim_id - 1]:
                    supporting.append(number)

            found[claim_id] = {"status": status, "supporting": supporting}

    verdicts = []

    for i in range(len(claims)):
        status = "unsupported"
        supporting = []

        if (i + 1) in found:
            status = found[i + 1]["status"]
            supporting = found[i + 1]["supporting"]

        # A claim cannot be supported without pointing to evidence
        if status != "unsupported" and len(supporting) == 0:
            status = "unsupported"

        # Citation validation: a citation is valid only if that source really supports the claim
        valid = []
        invalid = []
        for number in claims[i]["cited"]:
            if number in supporting:
                valid.append(number)
            else:
                invalid.append(number)

        verdicts.append(
            {
                "claim": claims[i]["claim"],
                "status": status,
                "cited": claims[i]["cited"],
                "supporting": supporting,
                "valid_citations": valid,
                "invalid_citations": invalid,
            }
        )

    return verdicts


# Phase 6 (Claim verification): check every claim against evidence and validate its citations
def verify_claims(claims, owner_id, answer_chunks):
    if len(claims) == 0:
        return {
            "verdicts": [],
            "pool": answer_chunks,
            "prompt_tokens": 0,
            "output_tokens": 0,
            "latency": 0,
        }

    pool, candidates = match_evidence(claims, owner_id, answer_chunks)
    result = generate_text(build_verify_prompt(claims, candidates, pool))

    return {
        "verdicts": parse_verdicts(result["text"], claims, candidates),
        "pool": pool,
        "prompt_tokens": result["prompt_tokens"],
        "output_tokens": result["output_tokens"],
        "latency": result["latency"],
    }
