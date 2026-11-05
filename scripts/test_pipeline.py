import json

from paperlens.ingestion.pipeline import ingest_pdf

chunks = ingest_pdf("data/raw/paper1.pdf", "paper1")

print("Total chunks:", len(chunks))
print("First chunk id:", chunks[0]["chunk_id"])
print("Last chunk id:", chunks[-1]["chunk_id"])

# Save the chunks so you can open and read them in VS Code
with open("data/processed/paper1_chunks.json", "w") as f:
    json.dump(chunks, f, indent=2)

print("Saved to data/processed/paper1_chunks.json")
