from paperlens.ingestion.loader import load_pdf
from paperlens.ingestion.cleaner import clean_text, fix_hyphenation
from paperlens.ingestion.section_detector import detect_sections
from paperlens.ingestion.chunker import group_by_section, make_chunks
from paperlens.ingestion.metadata import add_metadata

pages = load_pdf("data/raw/paper1.pdf")

for page in pages:
    text = clean_text(page["text"])
    text = fix_hyphenation(text)
    page["text"] = text

lines = detect_sections(pages)
groups = group_by_section(lines)
chunks = make_chunks(groups)
chunks = add_metadata(chunks, "paper1", "paper1.pdf")

print("Total chunks:", len(chunks))

# Check: every chunk id must be unique
ids = []
for chunk in chunks:
    ids.append(chunk["chunk_id"])
print("Unique ids:", len(set(ids)) == len(ids))

# Show the ID card of the first 2 chunks (without the long text)
for chunk in chunks[:2]:
    print("---")
    for key in chunk:
        if key != "text":
            print(key, ":", chunk[key])
