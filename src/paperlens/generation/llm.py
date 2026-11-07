import os
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL")
MAX_TRIES = 5

# Generation step (LLM): one client for the whole project
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# Generation step (LLM): check if an error is temporary, so trying again can help
def is_temporary_error(error):
    message = str(error)

    for word in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"]:
        if word in message:
            return True

    return False


# Generation step (LLM): send a prompt to Gemini and return the text, token counts and latency
def generate_text(prompt):
    if os.getenv("GEMINI_API_KEY") is None or MODEL_NAME is None:
        raise ValueError("GEMINI_API_KEY or GEMINI_MODEL is missing in the .env file")

    response = None
    latency = 0

    for attempt in range(MAX_TRIES):
        start = time.time()

        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            latency = time.time() - start
            break
        except Exception as error:
            if attempt == MAX_TRIES - 1 or not is_temporary_error(error):
                raise
            print("Gemini is busy, waiting before try", attempt + 2, "of", MAX_TRIES)
            time.sleep(10 * (attempt + 1))

    prompt_tokens = 0
    output_tokens = 0
    usage = response.usage_metadata
    if usage is not None:
        prompt_tokens = usage.prompt_token_count or 0
        output_tokens = usage.candidates_token_count or 0

    return {
        "text": response.text or "",
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "latency": round(latency, 2),
    }
