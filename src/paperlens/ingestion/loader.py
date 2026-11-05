import pymupdf


# Ingestion step 1 (Loader): read a PDF page by page, as plain text
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

                first = line["spans"][0]
                bold = (first["flags"] & 16) != 0 or "bold" in first["font"].lower()

                lines.append(
                    {
                        "page": page_index + 1,
                        "text": text,
                        "size": round(first["size"], 1),
                        "bold": bold,
                    }
                )

    doc.close()
    return lines
