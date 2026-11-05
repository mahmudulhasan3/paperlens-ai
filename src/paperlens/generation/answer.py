from paperlens.indexing.vector_store import search
from paperlens.generation.prompts import build_prompt, ABSTAIN_TEXT
from paperlens.generation.llm import generate_text


# Generation step (Citations): turn the [1], [2] numbers in the answer into real document and page references
def find_citations(answer, chunks):
    citations = []

    for i in range(len(chunks)):
        number = i + 1
        if "[" + str(number) + "]" in answer:
            meta = chunks[i]["metadata"]
            citations.append(
                {
                    "number": number,
                    "filename": meta["filename"],
                    "section": meta["section"],
                    "page_start": meta["page_start"],
                    "page_end": meta["page_end"],
                    "text": chunks[i]["text"],
                }
            )

    return citations


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

    return {
        "answer": answer,
        "abstained": ABSTAIN_TEXT in answer,
        "citations": find_citations(answer, chunks),
        "prompt_tokens": result["prompt_tokens"],
        "output_tokens": result["output_tokens"],
        "latency": result["latency"],
    }
