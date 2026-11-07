import pymupdf


# Ingestion step 1 (Loader): read a PDF page by page, as plain text
def load_pdf(pdf_path):
    pages = []
    doc = pymupdf.open(pdf_path)

    for page_index in range(len(doc)):
        page = doc[page_index]
        text = page.get_text()
        pages.append({
            "page": page_index + 1,
            "text": text,
        })

    doc.close()
    return pages


# Ingestion step 1 (Loader): read every line with its page, font size and bold flag
def load_pdf_lines(pdf_path):
    lines = []
    doc = pymupdf.open(pdf_path)

    for page_index in range(len(doc)):
        data = doc[page_index].get_text("dict")

        for block in data["blocks"]:
            if block["type"] != 0:
                continue

            for line in block["lines"]:
                text = ""
                for span in line["spans"]:
                    text = text + span["text"]
                text = " ".join(text.split())

                if text == "":
                    continue

                # A line is bold only if every span is bold; its size is the smallest span size
                all_bold = True
                smallest = None
                for span in line["spans"]:
                    if span["text"].strip() == "":
                        continue

                    is_bold = (span["flags"] & 16) != 0 or "bold" in span["font"].lower()
                    if not is_bold:
                        all_bold = False

                    if smallest is None or span["size"] < smallest:
                        smallest = span["size"]

                lines.append({
                    "page": page_index + 1,
                    "text": text,
                    "size": round(smallest, 1),
                    "bold": all_bold,
                })

    doc.close()
    return lines