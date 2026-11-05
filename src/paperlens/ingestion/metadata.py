# Ingestion step 5 (Metadata): attach document info and a unique id to every chunk
def add_metadata(chunks, doc_id, filename):
    result = []
    index = 0

    for chunk in chunks:
        chunk_id = doc_id + "_chunk_" + str(index)

        result.append(
            {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "filename": filename,
                "chunk_index": index,
                "section": chunk["section"],
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "word_count": len(chunk["text"].split()),
                "text": chunk["text"],
            }
        )

        index = index + 1

    return result
