from paperlens.generation.llm import generate_text


# Language step: a message is Bangla if it has at least one Bangla letter (Unicode block 0980 to 09FF)
def detect_language(text):
    for ch in text:
        if "\u0980" <= ch <= "\u09ff":
            return "bangla"

    return "english"


# Language step: translate a Bangla message into English, so retrieval and verification work on the English papers
def translate_to_english(text):
    prompt = "Translate the text below into English.\n"
    prompt = prompt + "Keep file names, numbers and technical terms unchanged.\n"
    prompt = prompt + "Reply with only the translation, nothing else.\n\n"
    prompt = prompt + "TEXT:\n" + text

    return generate_text(prompt)["text"].strip()


# Language step: translate an answer into Bangla and keep the source numbers and the formatting
def translate_to_bangla(text):
    prompt = "Translate the text below into Bangla (Bengali).\n"
    prompt = prompt + "Rules:\n"
    prompt = (
        prompt
        + "1. Keep every source number in square brackets exactly as it is, for example [1] or [2][3].\n"
    )
    prompt = (
        prompt
        + "2. Keep page references like (p. 5), file names, numbers and the markdown formatting (headings, bullet points, bold).\n"
    )
    prompt = (
        prompt
        + "3. Keep technical terms and names in English where this is natural in Bangla, for example RAG, LLM, dataset.\n"
    )
    prompt = prompt + "4. Do not add or remove any information.\n"
    prompt = prompt + "Reply with only the translation, nothing else.\n\n"
    prompt = prompt + "TEXT:\n" + text

    return generate_text(prompt)["text"].strip()
