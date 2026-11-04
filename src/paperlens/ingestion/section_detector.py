HEADINGS = [
    "abstract",
    "introduction",
    "related work",
    "background",
    "methodology",
    "methods",
    "method",
    "approach",
    "experiments",
    "experimental setup",
    "results",
    "discussion",
    "limitations",
    "conclusion",
    "conclusions",
    "future work",
    "references",
    "acknowledgements",
]


def get_heading(line):
    text = line.strip()
    parts = text.split(" ", 1)

    if len(parts) == 2 and parts[0].replace(".", "").isdigit():
        text = parts[1]

    text = text.lower()

    if text in HEADINGS:
        return text.title()
    return None


def detect_sections(pages):
    labeled_lines = []
    current_section = "Front Matter"

    for page in pages:
        lines = page["text"].split("\n")

        for line in lines:
            heading = get_heading(line)
            if heading is not None:
                current_section = heading

            labeled_lines.append(
                {
                    "page": page["page"],
                    "section": current_section,
                    "text": line,
                }
            )

    return labeled_lines
