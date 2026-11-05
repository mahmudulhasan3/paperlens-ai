from paperlens.ingestion.loader import load_pdf
from paperlens.ingestion.cleaner import clean_text, fix_hyphenation


# Debug helper: show 40 characters starting from a word, or say it was not found
def show(label, text, word):
    pos = text.find(word)
    if pos == -1:
        print(label, "NOT FOUND")
    else:
        print(label, repr(text[pos : pos + 40]))


pages = load_pdf("data/raw/paper1.pdf")
raw = pages[0]["text"]

# Debug: same text after cleaning and hyphen fixing
fixed = fix_hyphenation(clean_text(raw))

show("RAW tenden:", raw, "tenden")
show("FIXED tenden:", fixed, "tenden")
show("RAW adoption:", raw, "adoption")
show("FIXED adoption:", fixed, "adoption")
