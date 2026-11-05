# Ingestion step 2 (Cleaning): collapse repeated spaces and remove empty lines
def clean_text(text):
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line = " ".join(line.split())
        if line != "":
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# Ingestion step 2 (Cleaning): join words split by a hyphen at the end of a line (plain text version)
def fix_hyphenation(text):
    lines = text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.endswith("-") and i + 1 < len(lines):
            next_line = lines[i + 1]
            lines[i + 1] = line[:-1] + next_line
            i = i + 1
            continue

        result.append(line)
        i = i + 1

    return "\n".join(result)


# Ingestion step 2 (Cleaning): join words split by a hyphen, on lines that carry page and section labels
def fix_hyphenation_in_lines(labeled_lines):
    result = []
    i = 0

    while i < len(labeled_lines):
        item = labeled_lines[i]
        text = item["text"]

        if text.endswith("-") and i + 1 < len(labeled_lines):
            next_item = labeled_lines[i + 1]

            if next_item["section"] == item["section"]:
                labeled_lines[i + 1] = {
                    "page": next_item["page"],
                    "section": next_item["section"],
                    "text": text[:-1] + next_item["text"],
                }
                i = i + 1
                continue

        result.append(item)
        i = i + 1

    return result
