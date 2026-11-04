from paperlens.ingestion.cleaner import clean_text

messy = "Abstract   \n\n\nIn this   paper,   we study   RAG.\n   \nResults"

print("BEFORE:")
print(repr(messy))

print("AFTER:")
print(repr(clean_text(messy)))
