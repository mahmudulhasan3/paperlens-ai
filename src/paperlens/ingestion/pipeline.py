import os

from paperlens.ingestion.loader import load_pdf_lines
from paperlens.ingestion.cleaner import fix_hyphenation_in_lines
from paperlens.ingestion.section_detector import detect_sections_by_style
from paperlens.ingestion.chunker import group_by_section, make_chunks
from paperlens.ingestion.metadata import add_metadata


# Ingestion pipeline: run every ingestion step for one PDF and return its chunks
def ingest_pdf(pdf_path, doc_id, owner_id, file_hash, filename=None):
    if filename is None:
        filename = os.path.basename(pdf_path)

    # Step 1: load every line with its page and font style
    style_lines = load_pdf_lines(pdf_path)

    # Step 2: label every line with its section, using the PDF's own formatting
    labeled_lines = detect_sections_by_style(style_lines)

    # Step 3: join words split across lines
    labeled_lines = fix_hyphenation_in_lines(labeled_lines)

    # Step 4: cut the text into chunks inside each section
    groups = group_by_section(labeled_lines)
    chunks = make_chunks(groups)

    # Safety check: scanned PDFs have no extractable text
    if len(chunks) == 0:
        raise ValueError("No text found in " + filename + " (maybe a scanned PDF)")

    # Step 5: attach metadata, including the owner, to every chunk
    return add_metadata(chunks, doc_id, filename, owner_id, file_hash)
