# Ingestion step 3 (Sections): find the body font size (the size used for the most characters)
def find_body_size(style_lines):
    counts = {}

    for item in style_lines:
        size = item["size"]
        counts[size] = counts.get(size, 0) + len(item["text"])

    best_size = 0
    best_count = 0
    for size in counts:
        if counts[size] > best_count:
            best_size = size
            best_count = counts[size]

    return best_size


# Ingestion step 3 (Sections): find running headers and footers (same text on 3 or more pages)
def find_repeated_lines(style_lines):
    pages_of_text = {}

    for item in style_lines:
        text = item["text"]
        if text not in pages_of_text:
            pages_of_text[text] = []
        if item["page"] not in pages_of_text[text]:
            pages_of_text[text].append(item["page"])

    repeated = []
    for text in pages_of_text:
        if len(pages_of_text[text]) >= 3 and len(text.split()) >= 2:
            repeated.append(text)

    return repeated


# Ingestion step 3 (Sections): decide if one line looks like a heading
def is_heading_line(item, body_size):
    text = item["text"]
    words = text.split()

    has_letter = False
    for ch in text:
        if ch.isalpha():
            has_letter = True
    if not has_letter:
        return False

    if len(words) > 12:
        return False
    if text.endswith(".") or text.endswith(",") or text.endswith("-"):
        return False
    if not (text[0].isupper() or text[0].isdigit()):
        return False

    # Figure and table captions are never section headings
    lowered = text.lower()
    for start in ["figure ", "fig. ", "fig ", "table "]:
        if lowered.startswith(start):
            return False

    bigger = item["size"] >= body_size + 1
    bold_text = item["bold"] and item["size"] >= body_size - 0.5

    return bigger or bold_text


# Ingestion step 3 (Sections): label every line with its page and current section
def detect_sections_by_style(style_lines):
    body_size = find_body_size(style_lines)
    repeated = find_repeated_lines(style_lines)

    labeled_lines = []
    current_section = "Front Matter"
    previous_was_heading = False
    last_size = None
    last_page = None

    for item in style_lines:
        text = item["text"]

        if text in repeated:
            continue

        if is_heading_line(item, body_size):
            if (
                previous_was_heading
                and item["size"] == last_size
                and item["page"] == last_page
            ):
                current_section = current_section + " " + text
                labeled_lines[-1]["section"] = current_section
            else:
                current_section = text

            labeled_lines.append(
                {
                    "page": item["page"],
                    "section": current_section,
                    "text": text,
                }
            )
            previous_was_heading = True
            last_size = item["size"]
            last_page = item["page"]
        else:
            labeled_lines.append(
                {
                    "page": item["page"],
                    "section": current_section,
                    "text": text,
                }
            )
            previous_was_heading = False

    return labeled_lines
