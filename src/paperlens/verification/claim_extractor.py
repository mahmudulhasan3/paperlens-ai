import json

from paperlens.generation.llm import generate_text


# Phase 6 (Claim extraction): the instructions that ask Gemini to split an answer into single facts
# Phase 6 (Claim extraction): the instructions that ask Gemini to split an answer into single facts
def build_claim_prompt(answer):
    prompt = "Split the answer below into individual factual claims.\n"
    prompt = prompt + "Rules:\n"
    prompt = (
        prompt
        + "1. Every claim must be one single fact, written as a complete sentence that makes sense on its own.\n"
    )
    prompt = (
        prompt
        + "2. If a sentence contains several facts (for example a result and the data it was measured on), write each fact as its own claim.\n"
    )
    prompt = (
        prompt
        + "3. Do not add, change or improve any fact. Use only what the answer says.\n"
    )
    prompt = (
        prompt
        + "4. For each claim, list the source numbers written next to it in the answer. For example [1][2] becomes [1, 2]. Use an empty list if there is none.\n"
    )
    prompt = (
        prompt
        + "5. Skip opinions, greetings and sentences that are not factual claims.\n"
    )
    prompt = (
        prompt
        + "Example: 'The tool is written in Python and was tested on 20 users [1]' becomes two claims: "
    )
    prompt = (
        prompt
        + "'The tool is written in Python.' and 'The tool was tested on 20 users.', both with cited [1].\n"
    )
    prompt = prompt + "Reply with only a JSON list, nothing else, in this form:\n"
    prompt = prompt + '[{"claim": "...", "cited": [1, 2]}]\n\n'
    prompt = prompt + "ANSWER:\n" + answer

    return prompt


# Phase 6 (Claim extraction): read the JSON list from Gemini's reply, even if it adds code fences or extra words
def parse_claims(reply):
    start = reply.find("[")
    end = reply.rfind("]")

    if start == -1 or end == -1:
        return []

    try:
        data = json.loads(reply[start : end + 1])
    except ValueError:
        return []

    claims = []
    for item in data:
        if not isinstance(item, dict):
            continue

        text = str(item.get("claim", "")).strip()
        if text == "":
            continue

        cited = []
        for number in item.get("cited", []):
            if isinstance(number, int):
                cited.append(number)

        claims.append({"claim": text, "cited": cited})

    return claims


# Phase 6 (Claim extraction): break one answer into single factual claims
def extract_claims(answer):
    result = generate_text(build_claim_prompt(answer))

    return {
        "claims": parse_claims(result["text"]),
        "prompt_tokens": result["prompt_tokens"],
        "output_tokens": result["output_tokens"],
        "latency": result["latency"],
    }
