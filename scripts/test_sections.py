from paperlens.ingestion.loader import load_pdf
from paperlens.ingestion.cleaner import clean_text, fix_hyphenation
from paperlens.ingestion.section_detector import detect_sections

pages = load_pdf("data/raw/paper1.pdf")

for page in pages:
    text = clean_text(page["text"])
    text = fix_hyphenation(text)
    page["text"] = text

lines = detect_sections(pages)

last_section = None
for item in lines:
    if item["section"] != last_section:
        print("Page", item["page"], "->", item["section"])
        last_section = item["section"]
