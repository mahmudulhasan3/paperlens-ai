MIN_SECTION_WORDS = 40


# Ingestion step 4 (Chunking): join very short sections into the section before them
def merge_small_groups(groups):
    merged = []

    for group in groups:
        if len(group["words"]) < MIN_SECTION_WORDS and len(merged) > 0:
            merged[-1]["words"] = merged[-1]["words"] + group["words"]
        else:
            merged.append(group)

    return merged


# Ingestion step 4 (Chunking): group the labeled words under their section
def group_by_section(labeled_lines):
    groups = []
    current_section = None

    for item in labeled_lines:
        if item["section"] != current_section:
            groups.append({"section": item["section"], "words": []})
            current_section = item["section"]

        for word in item["text"].split():
            groups[-1]["words"].append({"word": word, "page": item["page"]})

    return merge_small_groups(groups)


# Ingestion step 4 (Chunking): cut each section into overlapping chunks
def make_chunks(groups, chunk_size=200, overlap=40):
    chunks = []
    step = chunk_size - overlap

    for group in groups:
        words = group["words"]
        start = 0

        while start < len(words):
            end = start + chunk_size
            piece = words[start:end]

            chunk_words = []
            for w in piece:
                chunk_words.append(w["word"])

            chunks.append(
                {
                    "text": " ".join(chunk_words),
                    "section": group["section"],
                    "page_start": piece[0]["page"],
                    "page_end": piece[-1]["page"],
                }
            )

            if end >= len(words):
                break
            start = start + step

    return chunks
