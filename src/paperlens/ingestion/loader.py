import pymupdf


def load_pdf(pdf_path):
    pages = []
    doc = pymupdf.open(pdf_path)

    for page_index in range(len(doc)):
        page = doc[page_index]
        text = page.get_text()
        pages.append(
            {
                "page": page_index + 1,
                "text": text,
            }
        )

    doc.close()
    return pages
