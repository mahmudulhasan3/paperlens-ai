from paperlens.ingestion.loader import load_pdf
from paperlens.ingestion.cleaner import clean_text, fix_hyphenation
from paperlens.ingestion.section_detector import detect_sections
from paperlens.ingestion.chunker import group_by_section, make_chunks

pages = load_pdf("data/raw/paper1.pdf")

# Debug: keep the raw text of page 1 so we can compare later
raw = pages[0]["text"]
start = raw.find("tendencies")
print("RAW tendencies:", repr(raw[start : start + 30]))

for page in pages:
    text = clean_text(page["text"])
    text = fix_hyphenation(text)
    page["text"] = text

# Debug: check the output of section detection (labeled lines)
lines = detect_sections(pages)
for item in lines:
    if "Faithfulness" in item["text"]:
        print("LINE:", repr(item["text"]))
        break

# Debug: check the first words after grouping by section
groups = group_by_section(lines)
first_words = []
for w in groups[0]["words"][:8]:
    first_words.append(w["word"])
print("WORDS:", first_words)

# Debug: check the text of the first chunk
chunks = make_chunks(groups)
print("CHUNK:", repr(chunks[0]["text"][:80]))
