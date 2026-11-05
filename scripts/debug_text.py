from paperlens.ingestion.loader import load_pdf
from paperlens.ingestion.cleaner import clean_text, fix_hyphenation

pages = load_pdf("data/raw/paper1.pdf")
raw = pages[0]["text"]

# Debug: show the same part of page 1 after each stage
cleaned = clean_text(raw)
fixed = fix_hyphenation(cleaned)

start = raw.find("Faithfulness")
print("RAW:", repr(raw[start : start + 60]))

start = cleaned.find("Faithfulness")
print("CLEANED:", repr(cleaned[start : start + 60]))

start = fixed.find("Faithfulness")
print("FIXED:", repr(fixed[start : start + 60]))
