from paperlens.ingestion.loader import load_pdf

pages = load_pdf("data/raw/paper1.pdf")

print("Total pages:", len(pages))
print("First page number:", pages[0]["page"])
print("First 500 characters of page 1:")
print(pages[0]["text"][:500])
