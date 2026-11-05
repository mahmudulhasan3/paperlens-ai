import os

from paperlens.ingestion.loader import load_pdf
from paperlens.ingestion.cleaner import clean_text, fix_hyphenation
from paperlens.ingestion.section_detector import detect_sections
from paperlens.ingestion.chunker import group_by_section, make_chunks
from paperlens.ingestion.metadata import add_metadata


# Ingestion pipeline: run every ingestion step for one PDF and return its chunks
def ingest_pdf(pdf_path, doc_id):
    filename = os.path.basename(pdf_path)

    # Step 1: load the PDF page by page
    pages = load_pdf(pdf_path)

    # Step 2: clean the text of every page
    for page in pages:
        text = clean_text(page["text"])
        text = fix_hyphenation(text)
        page["text"] = text

    # Step 3: label every line with its section
    lines = detect_sections(pages)

    # Step 4: cut the text into chunks inside each section
    groups = group_by_section(lines)
    chunks = make_chunks(groups)

    # Safety check: scanned PDFs have no extractable text
    if len(chunks) == 0:
        raise ValueError("No text found in " + filename + " (maybe a scanned PDF)")

    # Step 5: attach metadata to every chunk
    return add_metadata(chunks, doc_id, filename)
