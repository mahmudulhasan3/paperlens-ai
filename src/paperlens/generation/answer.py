from paperlens.indexing.vector_store import search
from paperlens.generation.prompts import build_prompt, ABSTAIN_TEXT
from paperlens.generation.llm import generate_text


# Citations step: renumber the source numbers in a text in the order in which they first appear (1, 2, 3, ...)
def renumber_citations(text, chunks):
    mapping = {}
    order = []
    result = ""
    i = 0

    while i < len(text):
        if text[i] == "[":
            end = text.find("]", i)

            if end != -1:
                parts = text[i + 1:end].replace(",", " ").split()
                all_numbers = len(parts) > 0
                for part in parts:
                    if not part.isdigit():
                        all_numbers = False

                if all_numbers:
                    for part in parts:
                        old = int(part)

                        # A source number that does not exist is dropped, so no fake citation stays in the text
                        if old < 1 or old > len(chunks):
                            continue

                        if old not in mapping:
                            mapping[old] = len(mapping) + 1
                            order.append(old)

                        result = result + "[" + str(mapping[old]) + "]"

                    i = end + 1
                    continue

        result = result + text[i]
        i = i + 1

    citations = []
    for old in order:
        meta = chunks[old - 1]["metadata"]
        citations.append({
            "number": mapping[old],
            "filename": meta["filename"],
            "section": meta["section"],
            "page_start": meta["page_start"],
            "page_end": meta["page_end"],
            "text": chunks[old - 1]["text"],
        })

    return {"text": result, "citations": citations}


# Phase 3 (Baseline RAG): dense search, then Gemini answers from the chunks, with no verification
def answer_baseline(question, owner_id, top_k=5):
    chunks = search(question, owner_id, top_k=top_k)

    # Basic abstention: no evidence at all means no LLM call
    if len(chunks) == 0:
        return {
            "answer": ABSTAIN_TEXT,
            "abstained": True,
            "citations": [],
            "prompt_tokens": 0,
            "output_tokens": 0,
            "latency": 0,
        }

    prompt = build_prompt(question, chunks)
    result = generate_text(prompt)
    answer = result["text"].strip()
    renumbered = renumber_citations(answer, chunks)

    return {
        "answer": renumbered["text"],
        "abstained": ABSTAIN_TEXT in answer,
        "citations": renumbered["citations"],
        "prompt_tokens": result["prompt_tokens"],
        "output_tokens": result["output_tokens"],
        "latency": result["latency"],
    }