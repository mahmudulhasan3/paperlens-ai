from paperlens.ingestion.loader import load_pdf
from paperlens.ingestion.cleaner import clean_text, fix_hyphenation
from paperlens.ingestion.section_detector import detect_sections
from paperlens.ingestion.chunker import group_by_section, make_chunks

pages = load_pdf("data/raw/paper1.pdf")

for page in pages:
    text = clean_text(page["text"])
    text = fix_hyphenation(text)
    page["text"] = text

lines = detect_sections(pages)
groups = group_by_section(lines)
chunks = make_chunks(groups)

print("Total chunks:", len(chunks))

for chunk in chunks[:5]:
    word_count = len(chunk["text"].split())
    print("---")
    print("Section:", chunk["section"])
    print("Pages:", chunk["page_start"], "to", chunk["page_end"])
    print("Words:", word_count)
    print(chunk["text"][:150])
