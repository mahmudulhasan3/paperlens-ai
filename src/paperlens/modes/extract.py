from paperlens.indexing.vector_store import search_document
from paperlens.generation.prompts import build_context
from paperlens.generation.answer import find_citations
from paperlens.generation.llm import generate_text

NOT_STATED = "Not stated in the document."


# Phase 5 (Extract): the instructions that ask Gemini to pull out only the requested information
def build_extract_prompt(request, chunks):
    prompt = "You extract specific information from a research paper.\n"
    prompt = (
        prompt
        + "Extract ONLY what the request asks for, using ONLY the numbered sources below.\n"
    )
    prompt = prompt + "Rules:\n"
    prompt = (
        prompt
        + "1. Answer as a short bullet list. Keep the wording close to the sources.\n"
    )
    prompt = (
        prompt
        + "2. After every bullet, add the source number in square brackets, for example [1].\n"
    )
    prompt = prompt + "3. Write two sources as [1][2]. Never write [1, 2].\n"
    prompt = prompt + "4. Do not add anything that is not in the sources.\n"
    prompt = (
        prompt
        + "5. If the sources do not contain the requested information, reply with exactly: "
        + NOT_STATED
        + "\n\n"
    )
    prompt = prompt + "SOURCES:\n" + build_context(chunks) + "\n"
    prompt = prompt + "REQUEST: " + request + "\n\n"
    prompt = prompt + "EXTRACTED INFORMATION:"

    return prompt


# Phase 5 (Extract): pull one kind of information out of one document
def extract_from_document(owner_id, doc_id, request, top_k=6):
    chunks = search_document(request, owner_id, doc_id, top_k=top_k)

    if len(chunks) == 0:
        raise ValueError("Document not found")

    result = generate_text(build_extract_prompt(request, chunks))
    extracted = result["text"].strip()

    return {
        "extracted": extracted,
        "not_found": NOT_STATED in extracted,
        "citations": find_citations(extracted, chunks),
        "prompt_tokens": result["prompt_tokens"],
        "output_tokens": result["output_tokens"],
        "latency": result["latency"],
    }
