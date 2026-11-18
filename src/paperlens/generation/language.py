from paperlens.generation.llm import generate_text

# Language step: common Bangla words written with English letters (Banglish), none of them is a normal English word
BANGLISH_WORDS = [
    "ami",
    "amar",
    "amake",
    "tumi",
    "tomar",
    "tomake",
    "apni",
    "apnar",
    "amra",
    "tara",
    "se",
    "shey",
    "ki",
    "kivabe",
    "kibhabe",
    "kemon",
    "keno",
    "kothay",
    "kobe",
    "kon",
    "koto",
    "kara",
    "kake",
    "eta",
    "ota",
    "eita",
    "oita",
    "ekta",
    "ekti",
    "ei",
    "oi",
    "sei",
    "shei",
    "ey",
    "er",
    "ta",
    "theke",
    "jonno",
    "niye",
    "shomporke",
    "somporke",
    "bishoye",
    "moddhe",
    "bolo",
    "bolun",
    "dao",
    "den",
    "dekhao",
    "dekhan",
    "bujhao",
    "bujhiye",
    "likho",
    "likhun",
    "khuje",
    "khujo",
    "korbo",
    "kore",
    "koro",
    "korun",
    "kora",
    "korechhe",
    "koreche",
    "korte",
    "hoy",
    "hobe",
    "hoyeche",
    "hoyechhe",
    "holo",
    "ache",
    "achhe",
    "nai",
    "nei",
    "ar",
    "ebong",
    "kintu",
    "tobe",
    "jodi",
    "tahole",
    "tahle",
    "tai",
    "shob",
    "sob",
    "onek",
    "khub",
    "bhalo",
    "valo",
    "kharap",
    "kono",
    "kichu",
    "kisu",
    "shudhu",
    "sudhu",
    "porikkha",
    "bangla",
    "banglay",
    "banglai",
    "bolbo",
    "bolche",
    "dekhi",
    "dekho",
    "janao",
    "jano",
    "bujhi",
    "bujhlam",
    "lagbe",
    "lage",
    "pabo",
    "pabe",
    "pai",
    "dorkar",
    "mane",
    "mone",
    "baniyeche",
    "likhechhe",
    "likheche",
]


# Language step: true if the text looks like Bangla written with English letters
def looks_like_banglish(text):
    words = []
    current = ""

    for ch in text.lower():
        if ch.isalpha():
            current = current + ch
        else:
            if current != "":
                words.append(current)
            current = ""
    if current != "":
        words.append(current)

    if len(words) == 0:
        return False

    markers = 0
    for word in words:
        if word in BANGLISH_WORDS:
            markers = markers + 1

    return markers >= 2 or markers / len(words) >= 0.34


# Language step: a message is Bangla if it has a Bangla letter (Unicode block 0980 to 09FF) or looks like Banglish
def detect_language(text):
    for ch in text:
        if "\u0980" <= ch <= "\u09ff":
            return "bangla"

    if looks_like_banglish(text):
        return "bangla"

    return "english"


# Language step: translate a Bangla or Banglish message into English, so retrieval and verification work on the English papers
def translate_to_english(text):
    prompt = "Translate the text below into English.\n"
    prompt = (
        prompt
        + "The text can be Bangla, or Bangla written with English letters (Banglish), or a mix with English words.\n"
    )
    prompt = prompt + "Keep file names, numbers and technical terms unchanged.\n"
    prompt = prompt + "Reply with only the translation, nothing else.\n\n"
    prompt = prompt + "TEXT:\n" + text

    return generate_text(prompt)["text"].strip()


# Language step: translate an answer into natural Bangla, technical words stay in English letters
def translate_to_bangla(text):
    prompt = "Translate the text below into natural, easy Bangla (Bengali script).\n"
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
        + "3. Write technical and academic words in English letters, never in Bangla letters. "
    )
    prompt = (
        prompt
        + "For example: RAG, LLM, dataset, embedding, retrieval, citation, evidence, model, accuracy, benchmark, "
    )
    prompt = (
        prompt
        + "fine-tuning, hallucination, faithfulness, paper, token, prompt, pipeline.\n"
    )
    prompt = (
        prompt
        + "4. Everything else must be normal Bangla sentences, not English sentences.\n"
    )
    prompt = prompt + "5. Do not add or remove any information.\n"
    prompt = prompt + "Reply with only the translation, nothing else.\n\n"
    prompt = prompt + "TEXT:\n" + text

    return generate_text(prompt)["text"].strip()
