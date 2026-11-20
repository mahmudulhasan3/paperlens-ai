import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from paperlens.generation.llm import is_temporary_error

load_dotenv()

EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIMENSIONS = 768
BATCH_SIZE = 50
MAX_TRIES = 5

# Phase 2 (Embeddings): one Gemini client, the model runs at Google and not in our server
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# Phase 2 (Embeddings): embed one batch of texts, and try again when Gemini is busy
def embed_batch(texts, task_type):
    for attempt in range(MAX_TRIES):
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBEDDING_DIMENSIONS,
                ),
            )

            vectors = []
            for item in response.embeddings:
                vectors.append(list(item.values))
            return vectors
        except Exception as error:
            if attempt == MAX_TRIES - 1 or not is_temporary_error(error):
                raise
            print("Gemini embeddings are busy, waiting before try", attempt + 2, "of", MAX_TRIES)
            time.sleep(5 * (attempt + 1))


# Phase 2 (Embeddings): turn the texts of document chunks into lists of numbers, 50 texts per request
def embed_texts(texts):
    vectors = []

    for start in range(0, len(texts), BATCH_SIZE):
        vectors = vectors + embed_batch(texts[start:start + BATCH_SIZE], "RETRIEVAL_DOCUMENT")

    return vectors


# Phase 2 (Embeddings): turn one question into a list of numbers (a question and a document use different task types)
def embed_query(text):
    return embed_batch([text], "RETRIEVAL_QUERY")[0]