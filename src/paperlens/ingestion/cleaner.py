def clean_text(text):
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line = " ".join(line.split())
        if line != "":
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


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
