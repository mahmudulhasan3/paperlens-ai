from paperlens.indexing.vector_store import list_documents
from paperlens.generation.llm import generate_text
from paperlens.generation.language import (
    detect_language,
    translate_to_english,
    translate_to_bangla,
)
from paperlens.generation.verified_answer import answer_verified
from paperlens.modes.summarize import summarize_document
from paperlens.modes.compare import compare_documents
from paperlens.modes.extract import extract_from_document

MODES = ["qa", "summarize", "compare", "extract"]

# Router step: the name of the main text field in the result of every mode
TEXT_KEYS = {
    "qa": "answer",
    "summarize": "summary",
    "compare": "comparison",
    "extract": "extracted",
}


# Phase 5 (Router): the instructions that ask Gemini for one label
def build_router_prompt(message):
    prompt = "Classify the user's message about uploaded research papers into exactly one label.\n"
    prompt = prompt + "Labels:\n"
    prompt = prompt + "qa: a question to be answered from the documents\n"
    prompt = prompt + "summarize: wants an overview or summary of a whole document\n"
    prompt = prompt + "compare: wants two or more documents compared\n"
    prompt = (
        prompt + "extract: wants one specific part or list pulled out of a document\n"
    )
    prompt = prompt + "Reply with only the label, nothing else.\n\n"
    prompt = prompt + "Examples:\n"
    prompt = prompt + "Give me an overview of the paper -> summarize\n"
    prompt = prompt + "How do these two papers differ? -> compare\n"
    prompt = prompt + "Find the future research directions -> extract\n"
    prompt = prompt + "What datasets were used? -> extract\n"
    prompt = prompt + "Why do language models post-rationalize citations? -> qa\n"
    prompt = prompt + "What is citation faithfulness? -> qa\n\n"
    prompt = prompt + "Message: " + message + "\nLabel:"

    return prompt


# Phase 5 (Router): decide the mode, using simple rules first and Gemini only if the rules do not match
def classify_intent(message):
    lowered = message.lower().strip()

    if lowered.startswith("summarize") or lowered.startswith("summarise"):
        return "summarize"
    if lowered.startswith("extract"):
        return "extract"
    if "compare" in lowered:
        return "compare"

    result = generate_text(build_router_prompt(message))
    words = result["text"].strip().lower().split()

    if len(words) > 0:
        label = words[0].strip(".,:;!\"'")
        if label in MODES:
            return label

    return "qa"


# Phase 5 (Router): find the documents whose file name appears in the message
def find_mentioned(message, docs):
    lowered = message.lower()
    mentioned = []

    for doc in docs:
        name = doc["filename"].lower()
        if name.endswith(".pdf"):
            name = name[:-4]
        if name in lowered:
            mentioned.append(doc)

    return mentioned


# Phase 5 (Router): ask the user which document, when it cannot be decided from the message
def need_document(mode, docs):
    return {"mode": mode, "needs_document": True, "documents": docs, "result": None}


# Phase 5 (Router, language): the result of a mode, translated into Bangla when the user wrote in Bangla
def finish(mode, result, language):
    if language == "bangla":
        key = TEXT_KEYS[mode]
        result[key] = translate_to_bangla(result[key])

    return {"mode": mode, "needs_document": False, "documents": [], "result": result}


# Phase 5 (Router): classify the message, pick the document(s) and run the right mode
def route_message(owner_id, message):
    docs = list_documents(owner_id)
    if len(docs) == 0:
        raise ValueError("Upload a PDF first")

    # Language step: all work is done in English, the final text is translated back for Bangla users
    language = detect_language(message)
    english_message = message
    if language == "bangla":
        english_message = translate_to_english(message)

    mode = classify_intent(english_message)
    mentioned = find_mentioned(message + " " + english_message, docs)

    if mode == "qa":
        result = answer_verified(english_message, owner_id, top_k=5)
        return finish(mode, result, language)

    if mode == "compare":
        if len(docs) < 2:
            raise ValueError("Upload at least two PDFs to compare them")

        if len(mentioned) >= 2:
            targets = mentioned
        elif len(docs) == 2:
            targets = docs
        else:
            return need_document(mode, docs)

        ids = []
        for doc in targets:
            ids.append(doc["doc_id"])
        result = compare_documents(owner_id, ids)
        return finish(mode, result, language)

    # summarize and extract work on one document
    if len(mentioned) == 1:
        target = mentioned[0]
    elif len(docs) == 1:
        target = docs[0]
    else:
        return need_document(mode, docs)

    if mode == "summarize":
        result = summarize_document(owner_id, target["doc_id"])
    else:
        result = extract_from_document(owner_id, target["doc_id"], english_message)

    return finish(mode, result, language)
