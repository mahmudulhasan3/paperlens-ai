from paperlens.ingestion.loader import load_pdf
from paperlens.ingestion.cleaner import clean_text, fix_hyphenation

sample = "information re-\ntrieval through\nchat"
print(repr(fix_hyphenation(sample)))

pages = load_pdf("data/raw/paper1.pdf")
text = clean_text(pages[0]["text"])
text = fix_hyphenation(text)
print(text[:700])
