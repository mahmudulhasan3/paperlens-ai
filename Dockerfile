# Docker step 1: start from a small Python image (the same Python version as in the venv)
FROM python:3.12-slim

# Docker step 2: no .pyc files, direct log output, and tell Python where our code is (src folder)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HF_HOME=/opt/hf-cache

# Docker step 3: the working folder inside the image
WORKDIR /app

# Docker step 4: install the packages first, so this slow layer is reused when only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Docker step 5: download the embedding model into the image, so a container never has to download it
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"
ENV HF_HUB_OFFLINE=1

# Docker step 6: copy only the code that the app needs (never the .env file)
COPY src ./src
COPY ui ./ui

# Docker step 7: run as a normal user, not as root
RUN useradd --create-home appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app /opt/hf-cache
USER appuser

# Docker step 8: the ports of the API and of the UI (this is only a note, compose opens them)
EXPOSE 8000 8501