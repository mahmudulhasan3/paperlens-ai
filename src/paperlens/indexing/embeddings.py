from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Phase 2 (Embeddings): load the embedding model once when this file is imported
model = SentenceTransformer(MODEL_NAME)


# Phase 2 (Embeddings): turn a list of texts into a list of number lists
def embed_texts(texts):
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()
